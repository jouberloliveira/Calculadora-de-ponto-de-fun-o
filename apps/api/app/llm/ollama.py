"""Async Ollama client with schema-aware retry.

Calls ``POST {url}/api/generate`` with ``stream=false`` and ``format=json``,
parses the ``response`` field, validates it against ``LLMAnalysis``. On
malformed output, retries with exponential backoff and an explicit
"reply with valid JSON only" reminder appended.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx
from pydantic import ValidationError

from app.fpa.models import LLMAnalysis

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Network / HTTP failure talking to Ollama."""


class OllamaInvalidResponse(Exception):
    """Ollama returned data that does not validate against the schema."""


class OllamaClient:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float = 300.0,
        max_retries: int = 3,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout_seconds
        self._max_retries = max(1, max_retries)
        self._client = client

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def health(self) -> bool:
        try:
            client = await self._get_client()
            resp = await client.get(f"{self._base_url}/api/tags", timeout=5.0)
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def analyze(
        self, *, system_prompt: str, user_prompt: str
    ) -> LLMAnalysis:
        """Call Ollama, parse JSON, validate. Retry on parse/validation errors."""
        last_err: Exception | None = None
        prompt = user_prompt
        for attempt in range(1, self._max_retries + 1):
            try:
                raw = await self._generate(system_prompt, prompt)
            except httpx.HTTPError as exc:
                raise OllamaError(f"Ollama HTTP error: {exc}") from exc

            try:
                parsed = _coerce_json(raw)
            except ValueError as exc:
                last_err = exc
                logger.warning(
                    "Ollama returned non-JSON on attempt %d: %s", attempt, exc
                )
                prompt = _retry_prompt(user_prompt, str(exc))
                await asyncio.sleep(_backoff(attempt))
                continue

            try:
                return LLMAnalysis.model_validate(parsed)
            except ValidationError as exc:
                last_err = exc
                logger.warning(
                    "Ollama JSON failed schema validation on attempt %d: %s",
                    attempt,
                    exc,
                )
                prompt = _retry_prompt(user_prompt, _short_validation_error(exc))
                await asyncio.sleep(_backoff(attempt))
                continue

        raise OllamaInvalidResponse(
            f"Ollama failed to return a valid response after "
            f"{self._max_retries} attempts: {last_err}"
        )

    async def _generate(self, system: str, prompt: str) -> str:
        client = await self._get_client()
        body: dict[str, Any] = {
            "model": self._model,
            "system": system,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1},
        }
        resp = await client.post(f"{self._base_url}/api/generate", json=body)
        resp.raise_for_status()
        data = resp.json()
        return str(data.get("response", ""))


def _coerce_json(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if not raw:
        raise ValueError("empty response")
    # Strip Markdown fences if a model ignored format=json.
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        # Last-ditch attempt: locate first '{' .. last '}'.
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                pass
        raise ValueError(f"invalid JSON: {exc.msg}") from exc


def _retry_prompt(original: str, problem: str) -> str:
    return (
        f"{original}\n\n"
        f"Your previous reply was invalid: {problem}. "
        "Reply ONLY with a valid JSON object matching the schema. "
        "No prose, no markdown fences."
    )


def _short_validation_error(exc: ValidationError) -> str:
    errs = exc.errors()
    if not errs:
        return "schema validation failed"
    first = errs[0]
    loc = ".".join(str(p) for p in first.get("loc", []))
    return f"{loc}: {first.get('msg', 'invalid')}"


def _backoff(attempt: int) -> float:
    return min(2.0, 0.25 * (2 ** (attempt - 1)))
