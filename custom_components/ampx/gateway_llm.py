"""Run a Home Assistant chat log against the AI gateway: tools, streaming, structured output.

Shared by AmpX's own conversation agent and AI Task entity (vendored from omniroute-ha)."""

from __future__ import annotations

import base64
import json
import re
from collections.abc import AsyncGenerator, AsyncIterator, Callable
from mimetypes import guess_file_type
from pathlib import Path
import logging
from typing import Any

import voluptuous as vol
from homeassistant.components import conversation
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import llm
from homeassistant.helpers.json import json_dumps
from homeassistant.util import ulid
from voluptuous_openapi import UNSUPPORTED, convert

from .gateway import GatewayClient, GatewayError


LOGGER = logging.getLogger(__name__)
MAX_TOOL_ITERATIONS = 10
STRUCTURED_AUTO = "auto"
STRUCTURED_JSON_SCHEMA = "json_schema"
STRUCTURED_JSON_OBJECT = "json_object"
STRUCTURED_PROMPT = "prompt"
STRUCTURED_MODES = [STRUCTURED_AUTO, STRUCTURED_JSON_SCHEMA, STRUCTURED_JSON_OBJECT, STRUCTURED_PROMPT]


def format_tool(tool: llm.Tool, custom_serializer: Callable[[Any], Any] | None) -> dict[str, Any]:
    """An HA LLM tool as an OpenAI function tool."""
    fn: dict[str, Any] = {
        "name": tool.name,
        "parameters": convert(tool.parameters, custom_serializer=custom_serializer),
    }
    if tool.description:
        fn["description"] = tool.description
    return {"type": "function", "function": fn}


def _unsupported(value: Any) -> bool:
    # voluptuous_openapi's sentinel: an object() in older releases, an `_Unsupported` instance in newer ones
    return value is UNSUPPORTED or type(value).__name__ == "_Unsupported"


def _sanitize(node: Any) -> Any:
    """Drop the parts of a JSON schema that HA could not translate, keeping the rest usable."""
    if isinstance(node, dict):
        out: dict[str, Any] = {}
        dropped: set[str] = set()
        for key, value in node.items():
            if _unsupported(value):
                continue
            if key == "properties" and isinstance(value, dict):
                props = {}
                for name, prop in value.items():
                    if _unsupported(prop):
                        dropped.add(name)
                        continue
                    props[name] = _sanitize(prop)
                out[key] = props
                continue
            out[key] = _sanitize(value)
        if dropped and isinstance(out.get("required"), list):
            out["required"] = [r for r in out["required"] if r not in dropped]
        return out
    if isinstance(node, list):
        return [_sanitize(v) for v in node if not _unsupported(v)]
    return node


_SKIPPED_TOOLS: set[str] = set()


def format_tools(tools: list[llm.Tool], custom_serializer: Callable[[Any], Any] | None) -> list[dict[str, Any]]:
    """Tools the gateway can be sent. One that still cannot be described as JSON is skipped, not fatal."""
    out = []
    for tool in tools:
        try:
            spec = format_tool(tool, custom_serializer)
            spec["function"]["parameters"] = _sanitize(spec["function"]["parameters"]) or {"type": "object", "properties": {}}
            json.dumps(spec)
        except (TypeError, ValueError) as err:
            # Once per tool: it is the same tool on every reply.
            level = logging.DEBUG if tool.name in _SKIPPED_TOOLS else logging.WARNING
            _SKIPPED_TOOLS.add(tool.name)
            LOGGER.log(level, "Not offering tool %s to the AI gateway: its parameters cannot be described (%s)", tool.name, err)
            continue
        out.append(spec)
    return out


def to_message(content: conversation.Content) -> dict[str, Any] | None:
    """A chat-log entry as an OpenAI chat message."""
    if isinstance(content, conversation.ToolResultContent):
        return {"role": "tool", "tool_call_id": content.tool_call_id, "content": json_dumps(content.tool_result)}
    if content.role in ("system", "user"):
        return {"role": content.role, "content": content.content} if content.content else None
    if content.role == "assistant":
        msg: dict[str, Any] = {"role": "assistant", "content": content.content}
        if isinstance(content, conversation.AssistantContent) and content.tool_calls:
            msg["tool_calls"] = [
                {"id": c.id, "type": "function", "function": {"name": c.tool_name, "arguments": json_dumps(c.tool_args)}}
                for c in content.tool_calls
            ]
        return msg
    LOGGER.debug("Skipping chat-log content the API cannot take: %s", content)
    return None


def _tool_args(raw: Any) -> dict[str, Any]:
    """Arguments arrive as a JSON string (OpenAI) or already as an object (some local servers)."""
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        args = json.loads(raw)
    except ValueError as err:
        raise HomeAssistantError(f"The model sent tool arguments that are not JSON: {raw[:200]}") from err
    return args if isinstance(args, dict) else {"value": args}


def _tool_inputs(calls: list[dict[str, Any]]) -> list[llm.ToolInput]:
    out = []
    for call in calls:
        fn = call.get("function") or {}
        if not fn.get("name"):
            continue
        out.append(llm.ToolInput(id=call.get("id") or ulid.ulid_now(), tool_name=fn["name"], tool_args=_tool_args(fn.get("arguments"))))
    return out


def _text(value: Any) -> str | None:
    """Message content as text: a string, or a list of parts (some routed providers send those)."""
    if value is None or isinstance(value, str):
        return value or None
    if isinstance(value, list):
        out = "".join(p.get("text") or "" if isinstance(p, dict) else str(p) for p in value)
        return out or None
    return str(value)


def _reasoning(part: dict[str, Any]) -> str | None:
    # Gateways name it differently: reasoning_content (DeepSeek, vLLM, LiteLLM), reasoning (OpenRouter-style, Ollama)
    value = part.get("reasoning_content") or part.get("reasoning")
    return value if isinstance(value, str) and value else None


async def transform_message(message: dict[str, Any], tools: bool = True) -> AsyncGenerator[conversation.AssistantContentDeltaDict]:
    """A whole (non-streamed) assistant message as one chat-log delta."""
    delta: conversation.AssistantContentDeltaDict = {"role": "assistant", "content": _text(message.get("content"))}
    if thinking := _reasoning(message):
        delta["thinking_content"] = thinking
    if message.get("tool_calls") and tools:  # calls to tools never offered are dropped, not run
        delta["tool_calls"] = _tool_inputs(message["tool_calls"])
    yield delta


async def transform_stream(chunks: AsyncIterator[dict[str, Any]], tools: bool = True) -> AsyncGenerator[conversation.AssistantContentDeltaDict]:
    """Server-sent chunks as chat-log deltas. Tool calls are assembled by index and sent last."""
    yield {"role": "assistant"}
    calls: dict[int, dict[str, Any]] = {}
    async for chunk in chunks:
        for choice in chunk.get("choices") or []:
            delta = choice.get("delta") or {}
            if thinking := _reasoning(delta):
                yield {"thinking_content": thinking}
            if text := _text(delta.get("content")):
                yield {"content": text}
            for pos, part in enumerate(delta.get("tool_calls") or []):
                idx = part.get("index", pos)
                call = calls.setdefault(idx, {"id": None, "function": {"name": "", "arguments": ""}})
                if part.get("id"):
                    call["id"] = part["id"]
                fn = part.get("function") or {}
                if fn.get("name"):
                    call["function"]["name"] += fn["name"]
                args = fn.get("arguments")
                if isinstance(args, dict):
                    call["function"]["arguments"] = args  # sent whole, not as string pieces
                elif args:
                    call["function"]["arguments"] += args
    if calls and tools:
        yield {"tool_calls": _tool_inputs([calls[i] for i in sorted(calls)])}


def _schema_for(structure: vol.Schema, llm_api: llm.APIInstance | None) -> dict[str, Any]:
    return convert(structure, custom_serializer=llm_api.custom_serializer if llm_api else llm.selector_serializer)


def _strictify(schema: dict[str, Any]) -> None:
    """OpenAI strict mode: every property required, optional ones nullable, no extras."""
    if schema.get("type") == "object" and "properties" in schema:
        required = schema.setdefault("required", [])
        schema["additionalProperties"] = False
        for name, prop in schema["properties"].items():
            _strictify(prop)
            if name not in required:
                prop["type"] = [prop.get("type", "string"), "null"]
                required.append(name)
    elif schema.get("type") == "array" and "items" in schema:
        _strictify(schema["items"])


async def files_to_parts(hass: HomeAssistant, files: list[tuple[Path, str | None]]) -> list[dict[str, Any]]:
    """Images (and PDFs, where the gateway passes them on) as data-URI content parts."""

    def read() -> list[dict[str, Any]]:
        parts = []
        for path, mime in files:
            if not path.exists():
                raise HomeAssistantError(f"`{path}` does not exist")
            mime = mime or guess_file_type(path)[0]
            if not mime or not mime.startswith(("image/", "application/pdf")):
                raise HomeAssistantError(f"`{path}` is not an image or PDF")
            data = base64.b64encode(path.read_bytes()).decode()
            parts.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}})
        return parts

    return await hass.async_add_executor_job(read)


async def async_run_chat_log(
    hass: HomeAssistant,
    client: GatewayClient,
    entity_id: str,
    chat_log: conversation.ChatLog,
    *,
    model: str,
    stream: bool = True,
    temperature: float | None = None,
    max_tokens: int | None = None,
    structured: str = STRUCTURED_AUTO,
    structure_name: str | None = None,
    structure: vol.Schema | None = None,
) -> None:
    """Run the model over the chat log until it stops calling tools."""
    args: dict[str, Any] = {"model": model, "user": chat_log.conversation_id}
    if temperature is not None:
        args["temperature"] = temperature
    if max_tokens:
        args["max_tokens"] = int(max_tokens)
    if chat_log.llm_api:
        if tools := format_tools(chat_log.llm_api.tools, chat_log.llm_api.custom_serializer):
            args["tools"] = tools
    messages = [m for c in chat_log.content if (m := to_message(c))]

    last = chat_log.content[-1]
    if last.role == "user" and last.attachments:
        parts = await files_to_parts(hass, [(a.path, a.mime_type) for a in last.attachments])
        messages[-1]["content"] = [{"type": "text", "text": messages[-1]["content"]}, *parts]

    modes: list[str] = [""]
    schema: dict[str, Any] = {}
    if structure is not None:
        schema = _schema_for(structure, chat_log.llm_api)
        modes = [STRUCTURED_JSON_SCHEMA, STRUCTURED_JSON_OBJECT, STRUCTURED_PROMPT] if structured == STRUCTURED_AUTO else [structured]
        stream = False

    for _ in range(MAX_TOOL_ITERATIONS):
        for i, mode in enumerate(modes):
            payload = {**args, "messages": list(messages)}
            if mode:
                payload = _with_structure(payload, mode, structure_name or "result", schema)
            try:
                if stream:
                    source = transform_stream(client.async_stream_chat(payload), tools=chat_log.llm_api is not None)
                else:
                    result = await client.async_chat(payload)
                    source = transform_message(result["choices"][0].get("message") or {}, tools=chat_log.llm_api is not None)
                added = [c async for c in chat_log.async_add_delta_content_stream(entity_id, source)]
            except GatewayError as err:
                # A 4xx/5xx on response_format means this gateway or model cannot do it: step down.
                if mode and i + 1 < len(modes) and err.status in (400, 404, 415, 422, 500, 501):
                    LOGGER.debug("Structured output %s refused (%s); trying %s", mode, err, modes[i + 1])
                    continue
                raise HomeAssistantError(f"AI gateway error: {err}") from err
            except HomeAssistantError:
                raise
            except Exception as err:
                # Never let an odd reply surface as Assist's bare "Unexpected error during intent recognition".
                LOGGER.exception("Could not use the AI gateway's reply")
                raise HomeAssistantError(f"AI gateway reply could not be used ({type(err).__name__}: {err})") from err
            modes = [mode]  # keep what worked for the remaining tool rounds
            break
        messages.extend(m for c in added if (m := to_message(c)))
        if not chat_log.unresponded_tool_results:
            return


def parse_json_reply(text: str) -> Any:
    """JSON from a model reply, forgiving code fences and prose around the object."""
    m = re.match(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", text, re.S)
    if m:
        text = m.group(1)
    try:
        return json.loads(text)
    except ValueError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _with_structure(payload: dict[str, Any], mode: str, name: str, schema: dict[str, Any]) -> dict[str, Any]:
    payload = {**payload, "messages": list(payload["messages"])}
    if mode == STRUCTURED_JSON_SCHEMA:
        strict = json.loads(json.dumps(schema))
        _strictify(strict)
        payload["response_format"] = {"type": "json_schema", "json_schema": {"name": name, "strict": True, "schema": strict}}
        return payload
    hint = (
        "Reply with a single JSON object and nothing else, no prose and no code fences. "
        f"It must match this JSON schema:\n{json.dumps(schema)}"
    )
    payload["messages"].append({"role": "system", "content": hint})
    if mode == STRUCTURED_JSON_OBJECT:
        payload["response_format"] = {"type": "json_object"}
    return payload
