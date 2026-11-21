"""Async client for any OpenAI-compatible gateway (OmniRoute, LiteLLM, Ollama, vLLM, LM Studio).

Only plain HTTP and the shared aiohttp session: no openai SDK, so nothing to install and
nothing that assumes OpenAI's own quirks.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import aiohttp

LOGGER = logging.getLogger(__name__)


class GatewayError(Exception):
    """The gateway answered with an error."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class GatewayAuthError(GatewayError):
    """The gateway refused the API key."""


class GatewayConnectionError(GatewayError):
    """The gateway could not be reached."""


def normalize_base_url(url: str) -> str:
    """Trim what people paste: whitespace, trailing slashes, a full endpoint path."""
    url = url.strip().rstrip("/")
    for suffix in ("/chat/completions", "/completions", "/models"):
        if url.endswith(suffix):
            url = url[: -len(suffix)].rstrip("/")
    return url


def _error_text(body: str) -> str:
    try:
        data = json.loads(body)
    except ValueError:
        return body[:300]
    err = data.get("error", data) if isinstance(data, dict) else data
    if isinstance(err, dict):
        return str(err.get("message") or err)[:300]
    return str(err)[:300]


class GatewayClient:
    """Talks to ``{base_url}/models`` and ``{base_url}/chat/completions``."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        api_key: str | None = None,
        timeout: float = 60,
    ) -> None:
        self._session = session
        self.base_url = normalize_base_url(base_url)
        self._api_key = api_key or None
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    @property
    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "X-Title": "Home Assistant"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def _request(self, method: str, path: str, payload: dict[str, Any] | None = None, base: str | None = None) -> aiohttp.ClientResponse:
        url = f"{base or self.base_url}{path}"
        try:
            resp = await self._session.request(method, url, json=payload, headers=self._headers, timeout=self._timeout)
        except TimeoutError as err:
            raise GatewayConnectionError(f"Timed out talking to {url}") from err
        except aiohttp.ClientError as err:
            raise GatewayConnectionError(f"Cannot reach {url}: {err}") from err
        if resp.status in (401, 403):
            body = await resp.text()
            raise GatewayAuthError(f"Gateway refused the API key: {_error_text(body)}", resp.status)
        if resp.status >= 400:
            body = await resp.text()
            raise GatewayError(f"Gateway error {resp.status}: {_error_text(body)}", resp.status)
        return resp

    async def async_discover(self) -> list[str]:
        """List models, finding the API root if the ``/v1`` was left off.

        Adopts the working base URL on success, so callers should save ``self.base_url``.
        """
        candidates = [self.base_url]
        if not self.base_url.endswith("/v1"):
            candidates.append(f"{self.base_url}/v1")
        last: GatewayError | None = None
        for base in candidates:
            try:
                models = await self._list_models(base)
            except GatewayAuthError:
                raise
            except GatewayError as err:
                last = err
                continue
            self.base_url = base
            return models
        assert last is not None
        raise last

    async def async_list_models(self) -> list[str]:
        """Model ids the gateway offers, sorted."""
        return await self._list_models(self.base_url)

    async def _list_models(self, base: str) -> list[str]:
        resp = await self._request("GET", "/models", base=base)
        try:
            data = await resp.json(content_type=None)
        except ValueError as err:
            raise GatewayError(f"{base}/models did not return JSON") from err
        # OpenAI shape {"data": [{"id": ...}]}; tolerate a bare list and Ollama-style {"models": [...]}
        rows = data.get("data", data.get("models")) if isinstance(data, dict) else data
        if not isinstance(rows, list):
            raise GatewayError(f"{base}/models is not an OpenAI-style model list")
        ids = {str(r.get("id") or r.get("name") or r.get("model")) if isinstance(r, dict) else str(r) for r in rows}
        return sorted(i for i in ids if i and i != "None")

    async def async_chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        """One non-streaming chat completion."""
        resp = await self._request("POST", "/chat/completions", {**payload, "stream": False})
        try:
            data = await resp.json(content_type=None)
        except ValueError as err:
            raise GatewayError("Chat completion was not JSON") from err
        if not isinstance(data, dict) or not data.get("choices"):
            raise GatewayError(f"Chat completion has no choices: {str(data)[:200]}")
        return data

    async def async_stream_chat(self, payload: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        """Stream a chat completion, yielding each server-sent chunk as a dict."""
        resp = await self._request("POST", "/chat/completions", {**payload, "stream": True})
        if "json" in (resp.content_type or "") and "event-stream" not in (resp.content_type or ""):
            # Gateway ignored stream=true and answered in one piece: hand it on as one chunk.
            data = await resp.json(content_type=None)
            for choice in data.get("choices", []):
                choice.setdefault("delta", choice.get("message") or {})
            yield data
            return
        buffer = b""
        async for raw in resp.content:
            buffer += raw
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                text = line.decode("utf-8", "replace").strip()
                if not text.startswith("data:"):
                    continue  # comments, event names, keep-alives
                body = text[5:].strip()
                if body == "[DONE]":
                    return
                try:
                    chunk = json.loads(body)
                except ValueError:
                    LOGGER.debug("Skipping unparsable stream line: %s", body[:120])
                    continue
                if isinstance(chunk, dict) and "error" in chunk:
                    raise GatewayError(f"Gateway stream error: {_error_text(body)}")
                yield chunk
