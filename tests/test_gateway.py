"""AmpX's built-in AI gateway: any OpenAI-compatible server (OmniRoute, LiteLLM, Ollama, vLLM, LM Studio).

With a gateway URL set, AmpX offers its own conversation agent and AI Task entity backed by it,
and uses them for its own model calls unless another agent is chosen."""

import copy
import json

import pytest
import voluptuous as vol
from homeassistant.components import ai_task, conversation
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import Context, HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import llm, selector
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMockResponse

from custom_components.ampx.const import DEFAULTS, DOMAIN
from custom_components.ampx.migrate import LEGACY

BASE = "http://omni.local:20128/v1"
GW = {"gateway_url": BASE, "gateway_api_key": "sk-test", "gateway_model": "auto", "gateway_stream": False}


def completion(content=None, tool_calls=None):
    msg = {"role": "assistant", "content": content}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return {"model": "auto", "choices": [{"message": msg, "finish_reason": "stop"}]}


class Gateway:
    def __init__(self, mock, models=("auto", "gpt-4o-mini")):
        self.sent, self.replies = [], []
        mock.get(f"{BASE}/models", json={"data": [{"id": m} for m in models]})
        mock.post(f"{BASE}/chat/completions", side_effect=self._chat)

    def reply(self, body, status=200):
        self.replies.append((status, body))

    def stream(self, *chunks):
        body = "".join(f"data: {json.dumps(c)}\n\n" for c in chunks) + "data: [DONE]\n\n"
        self.replies.append((200, body.encode()))

    async def _chat(self, method, url, data):
        self.sent.append(copy.deepcopy(data))
        status, body = self.replies.pop(0)
        if isinstance(body, bytes):
            return AiohttpClientMockResponse(method, url, status=status, response=body, headers={"content-type": "text/event-stream"})
        return AiohttpClientMockResponse(method, url, status=status, json=body, headers={"content-type": "application/json"})


@pytest.fixture
def gateway(aioclient_mock):
    return Gateway(aioclient_mock)


async def _setup(hass: HomeAssistant, **opts):
    assert await async_setup_component(hass, "homeassistant", {})
    entry = MockConfigEntry(domain=DOMAIN, title="AmpX", data={}, options={**DEFAULTS, **LEGACY, **opts})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry, hass.data[DOMAIN][entry.entry_id]


async def test_no_gateway_no_extra_entities(hass, aioclient_mock):
    _, brain = await _setup(hass)
    assert brain.gateway is None
    assert not hass.states.async_entity_ids("conversation") or "conversation.ampx" not in hass.states.async_entity_ids("conversation")
    assert hass.states.get("ai_task.ampx_ai_task") is None


async def test_gateway_gives_agent_and_task(hass, gateway):
    _, brain = await _setup(hass, **GW)
    assert brain.gateway is not None and brain.gateway.base_url == BASE
    assert brain.gateway_agent == "conversation.ampx_assistant"
    assert hass.states.get("conversation.ampx_assistant") is not None
    assert brain.gateway_task == "ai_task.ampx_ai_task"
    assert hass.states.get("ai_task.ampx_ai_task") is not None


async def test_ask_agent_uses_gateway_by_default(hass, gateway):
    _, brain = await _setup(hass, **GW)
    gateway.reply(completion("Battery is full."))
    assert await brain.ask_agent("battery?") == "Battery is full."
    sent = gateway.sent[0]
    assert sent["model"] == "auto" and sent["messages"][-1] == {"role": "user", "content": "battery?"}
    assert any(t["function"]["name"] for t in sent.get("tools", []))  # Assist + AmpX tools offered


async def test_agent_streams_and_calls_ampx_tools(hass, gateway):
    class Ping(llm.Tool):
        name = "ping"
        description = "ping"
        parameters = vol.Schema({vol.Required("x"): int})
        seen: list = []

        async def async_call(self, hass, tool_input, llm_context):
            Ping.seen.append(tool_input.tool_args)
            return {"pong": True}

    class PingAPI(llm.API):
        async def async_get_api_instance(self, llm_context):
            return llm.APIInstance(self, "", llm_context, [Ping()])

    llm.async_register_api(hass, PingAPI(hass=hass, id="ping_api", name="Ping"))
    await _setup(hass, **{**GW, "gateway_stream": True, "gateway_llm_api": ["ping_api"]})
    gateway.stream({"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "a", "function": {"name": "ping", "arguments": '{"x": 3}'}}]}}]})
    gateway.stream({"choices": [{"delta": {"content": "pong"}}]})
    result = await conversation.async_converse(hass, "ping", None, Context(), agent_id="conversation.ampx_assistant")
    assert result.response.speech["plain"]["speech"] == "pong"
    assert Ping.seen == [{"x": 3}]
    assert gateway.sent[1]["messages"][-1]["role"] == "tool"


async def test_ai_task_structured_falls_back(hass, gateway):
    await _setup(hass, **{**GW, "gateway_task_model": "gpt-4o-mini"})
    gateway.reply({"error": {"message": "no json_schema"}}, status=400)
    gateway.reply(completion('```json\n{"who": "postie"}\n```'))
    structure = vol.Schema({vol.Required("who"): selector.TextSelector()})
    result = await ai_task.async_generate_data(hass, task_name="who", entity_id="ai_task.ampx_ai_task", instructions="Who?", structure=structure)
    assert result.data == {"who": "postie"}
    assert gateway.sent[0]["model"] == "gpt-4o-mini"
    assert [s.get("response_format", {}).get("type") for s in gateway.sent] == ["json_schema", "json_object"]


async def test_chosen_agent_still_wins(hass, gateway):
    _, brain = await _setup(hass, **GW, conversation_agent="conversation.home_assistant")
    calls = []

    async def fake_process(call):
        calls.append(call.data)
        return {"response": {"speech": {"plain": {"speech": "from HA"}}}}

    hass.services.async_register("conversation", "process", fake_process, supports_response=True)
    assert await brain.ask_agent("hi") == "from HA"
    assert calls[0]["agent_id"] == "conversation.home_assistant" and not gateway.sent


async def test_options_page_probes_and_saves(hass, aioclient_mock):
    aioclient_mock.get("http://box:11434/models", status=404, text="no")
    aioclient_mock.get("http://box:11434/v1/models", json={"data": [{"id": "llama3.1"}]})
    aioclient_mock.get("http://down/v1/models", exc=TimeoutError())
    entry, _ = await _setup(hass)
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    assert "gateway" in flow["menu_options"]
    flow = await hass.config_entries.options.async_configure(flow["flow_id"], {"next_step_id": "gateway"})
    bad = await hass.config_entries.options.async_configure(flow["flow_id"], {"gateway_url": "http://down/v1"})
    assert bad["type"] is FlowResultType.FORM and bad["errors"] == {"base": "cannot_connect"}
    ok = await hass.config_entries.options.async_configure(bad["flow_id"], {"gateway_url": "http://box:11434", "gateway_api_key": ""})
    assert ok["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["gateway_url"] == "http://box:11434/v1"  # /v1 found
    assert entry.options["gateway_api_key"] == ""
    assert entry.options["gateway_model"] == "llama3.1"  # first listed, no `auto` here


async def test_gateway_down_does_not_break_ampx(hass, aioclient_mock):
    aioclient_mock.get(f"{BASE}/models", exc=TimeoutError())
    entry, brain = await _setup(hass, **GW)
    assert entry.state is ConfigEntryState.LOADED
    assert brain.gateway is not None  # entities exist and error per call; AmpX keeps running


async def test_overview_shows_gateway_without_key(hass, gateway, hass_ws_client):
    await _setup(hass, **GW)
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "ampx/overview"})
    gw = (await ws.receive_json())["result"]["gateway"]
    assert gw == {"configured": True, "url": BASE, "model": "auto", "task_model": "auto", "agent": "conversation.ampx_assistant", "task": "ai_task.ampx_ai_task"}
    assert "sk-test" not in json.dumps(gw)


async def test_ask_action_defaults_to_gateway_agent(hass, gateway):
    await _setup(hass, **GW)
    gateway.reply(completion("Lights are off."))
    out = await hass.services.async_call(DOMAIN, "ask", {"question": "lights?", "speak": False}, blocking=True, return_response=True)
    assert out == {"answer": "Lights are off."}


async def test_dashboard_url_finds_api_at_root(hass, aioclient_mock):
    """Pasting OmniRoute's dashboard URL still works: the API is at <host>/v1."""
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    from custom_components.ampx.gateway import GatewayClient

    for path in ("/dashboard/models", "/dashboard/v1/models"):
        aioclient_mock.get(f"http://omni:20128{path}", text="<!doctype html><html>OmniRoute</html>", headers={"content-type": "text/html"})
    aioclient_mock.get("http://omni:20128/v1/models", json={"object": "list", "data": [{"id": "auto", "object": "model"}]})
    client = GatewayClient(async_get_clientsession(hass), "http://omni:20128/dashboard")
    assert await client.async_discover() == ["auto"]
    assert client.base_url == "http://omni:20128/v1"


async def test_options_error_says_what_came_back(hass, aioclient_mock):
    for path in ("/x/models", "/x/v1/models", "/v1/models"):
        aioclient_mock.get(f"http://web{path}", text="<html>login</html>", headers={"content-type": "text/html"})
    entry, _ = await _setup(hass)
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    flow = await hass.config_entries.options.async_configure(flow["flow_id"], {"next_step_id": "gateway"})
    bad = await hass.config_entries.options.async_configure(flow["flow_id"], {"gateway_url": "http://web/x"})
    assert bad["errors"] == {"base": "not_openai_compatible"}
    detail = bad["description_placeholders"]["error"]
    assert "http://web/x/models" in detail and "text/html" in detail and "<html>login" in detail
    assert "http://web/v1/models" in detail


@pytest.mark.parametrize("stream", [False, True])
async def test_content_as_parts_is_joined(hass, gateway, stream):
    """Some routed providers send content as a list of text parts."""
    await _setup(hass, **{**GW, "gateway_stream": stream})
    parts = [{"type": "text", "text": "Hello "}, {"type": "text", "text": "there"}]
    if stream:
        gateway.stream({"choices": [{"delta": {"role": "assistant", "content": parts}}]})
    else:
        gateway.reply({"choices": [{"message": {"role": "assistant", "content": parts}}]})
    res = await conversation.async_converse(hass, "hi", None, Context(), agent_id="conversation.ampx_assistant")
    assert res.response.speech["plain"]["speech"] == "Hello there"


@pytest.mark.parametrize("stream", [False, True])
async def test_tool_calls_without_tools_are_ignored(hass, gateway, stream):
    """A model that calls tools it was never offered must not crash the agent."""
    await _setup(hass, **{**GW, "gateway_stream": stream, "gateway_llm_api": []})
    call = [{"index": 0, "id": "t", "type": "function", "function": {"name": "HassTurnOn", "arguments": "{}"}}]
    if stream:
        gateway.stream({"choices": [{"delta": {"content": "On it."}}]}, {"choices": [{"delta": {"tool_calls": call}}]})
    else:
        gateway.reply(completion("On it.", call))
    res = await conversation.async_converse(hass, "lights on", None, Context(), agent_id="conversation.ampx_assistant")
    assert res.response.speech["plain"]["speech"] == "On it."
    assert len(gateway.sent) == 1


async def test_broken_stream_is_an_error_reply_not_a_crash(hass, aioclient_mock):
    """A stream cut off mid-way gives an error reply with the reason, never an exception."""
    aioclient_mock.get(f"{BASE}/models", json={"data": [{"id": "auto"}]})
    aioclient_mock.post(f"{BASE}/chat/completions", exc=TimeoutError())
    await _setup(hass, **{**GW, "gateway_stream": True})
    res = await conversation.async_converse(hass, "hi", None, Context(), agent_id="conversation.ampx_assistant")
    from homeassistant.helpers import intent

    assert res.response.response_type is intent.IntentResponseType.ERROR
    assert "gateway" in res.response.speech["plain"]["speech"].lower()


async def test_html_403_is_not_blamed_on_the_key(hass, aioclient_mock):
    """A Cloudflare/Vercel challenge page is a 403 with HTML: say so, don't say the key is wrong."""
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    from custom_components.ampx.gateway import GatewayAuthError, GatewayClient, GatewayError

    aioclient_mock.get("https://omni.example.com/v1/models", status=403, text="<!DOCTYPE html><title>Just a moment...</title>", headers={"content-type": "text/html"})
    aioclient_mock.get("https://key.example.com/v1/models", status=403, json={"error": {"message": "Invalid API key"}})
    s = async_get_clientsession(hass)
    with pytest.raises(GatewayError) as err:
        await GatewayClient(s, "https://omni.example.com/v1").async_discover()
    assert not isinstance(err.value, GatewayAuthError)
    assert "403" in str(err.value) and "Just a moment" in str(err.value) and "proxy" in str(err.value)
    with pytest.raises(GatewayAuthError):
        await GatewayClient(s, "https://key.example.com/v1").async_discover()
    assert aioclient_mock.mock_calls[0][3]["User-Agent"].startswith("HomeAssistant-AmpX")


def test_unsupported_schema_parts_are_dropped():
    """Newer voluptuous_openapi leaks an `_Unsupported` object for selectors HA cannot translate
    (e.g. a field on an exposed script). Those parts go; the rest of the tool stays usable."""
    from voluptuous_openapi import UNSUPPORTED

    from custom_components.ampx.gateway_llm import _sanitize

    class _Unsupported:  # the newer library's sentinel type
        pass

    leaked = {
        "type": "object",
        "properties": {
            "room": {"type": "string"},
            "weird": _Unsupported(),
            "old": UNSUPPORTED,
            "list": {"type": "array", "items": _Unsupported()},
            "either": {"anyOf": [{"type": "string"}, _Unsupported()]},
        },
        "required": ["room", "weird"],
    }
    clean = _sanitize(leaked)
    assert set(clean["properties"]) == {"room", "list", "either"}
    assert clean["required"] == ["room"]
    assert clean["properties"]["list"] == {"type": "array"}
    assert clean["properties"]["either"] == {"anyOf": [{"type": "string"}]}
    json.dumps(clean)


def test_tool_that_cannot_be_described_is_skipped():
    from custom_components.ampx.gateway_llm import format_tools

    class T(llm.Tool):
        name, description, parameters = "broken", "x", vol.Schema({vol.Required("x"): str})

    class Boom:
        pass

    def serializer(value):
        return {"type": "string", "default": Boom()} if value is str else llm.selector_serializer(value)

    assert format_tools([T()], serializer) == []
