"""Tests for the Ollama client retry / parsing logic."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from app.llm.ollama import OllamaClient, OllamaInvalidResponse

OLLAMA_URL = "http://test-ollama:11434"


def _make_client() -> OllamaClient:
    return OllamaClient(
        base_url=OLLAMA_URL,
        model="test-model",
        timeout_seconds=5.0,
        max_retries=3,
    )


@respx.mock
@pytest.mark.asyncio
async def test_ollama_retries_on_invalid_json_then_succeeds() -> None:
    valid_payload = {
        "functions": [
            {
                "type": "EI",
                "name": "Login",
                "complexity": "low",
                "justification": "user submits credentials",
            }
        ],
        "vafFactors": [
            {"name": "Data communications", "value": 3, "rationale": "web app"}
        ],
    }
    route = respx.post(f"{OLLAMA_URL}/api/generate").mock(
        side_effect=[
            httpx.Response(200, json={"response": "this is not JSON"}),
            httpx.Response(200, json={"response": json.dumps(valid_payload)}),
        ]
    )
    client = _make_client()
    try:
        result = await client.analyze(
            system_prompt="system", user_prompt="user"
        )
    finally:
        await client.close()
    assert route.call_count == 2
    assert len(result.functions) == 1
    assert result.functions[0].name == "Login"


@respx.mock
@pytest.mark.asyncio
async def test_ollama_retries_on_schema_violation_then_raises() -> None:
    bad_payload = {"functions": [], "vafFactors": []}  # empty functions -> invalid
    route = respx.post(f"{OLLAMA_URL}/api/generate").mock(
        return_value=httpx.Response(200, json={"response": json.dumps(bad_payload)})
    )
    client = OllamaClient(
        base_url=OLLAMA_URL, model="test-model", timeout_seconds=5.0, max_retries=2
    )
    try:
        with pytest.raises(OllamaInvalidResponse):
            await client.analyze(system_prompt="s", user_prompt="u")
    finally:
        await client.close()
    assert route.call_count == 2  # exhausted retries


@respx.mock
@pytest.mark.asyncio
async def test_ollama_strips_markdown_fences() -> None:
    valid_payload = {
        "functions": [
            {"type": "ILF", "name": "Users", "complexity": "low", "justification": ""}
        ],
        "vafFactors": [],
    }
    fenced = "```json\n" + json.dumps(valid_payload) + "\n```"
    respx.post(f"{OLLAMA_URL}/api/generate").mock(
        return_value=httpx.Response(200, json={"response": fenced})
    )
    client = _make_client()
    try:
        result = await client.analyze(system_prompt="s", user_prompt="u")
    finally:
        await client.close()
    assert result.functions[0].name == "Users"
