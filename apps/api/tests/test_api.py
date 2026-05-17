"""HTTP-level tests for the FastAPI app."""

from __future__ import annotations

import io
import json
import time
import zipfile

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.main import app

OLLAMA_URL = "http://test-ollama:11434"


def _zip_with(files: list[tuple[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files:
            zf.writestr(name, content)
    return buf.getvalue()


def test_healthz_returns_ok() -> None:
    with TestClient(app) as client:
        resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "ollama" in body


def test_analyze_rejects_empty_request() -> None:
    with TestClient(app) as client:
        resp = client.post("/analyze")
    # FastAPI 422 because `files` is required.
    assert resp.status_code == 422


def test_analyze_rejects_zip_slip_upload() -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        info = zipfile.ZipInfo(filename="../escape.txt")
        zf.writestr(info, b"pwned")
    with TestClient(app) as client:
        resp = client.post(
            "/analyze",
            files={"files": ("evil.zip", buf.getvalue(), "application/zip")},
        )
    assert resp.status_code == 400
    assert "escapes" in resp.json()["detail"] or "Unsafe" in resp.json()["detail"]


@respx.mock
def test_analyze_accepts_valid_upload_and_returns_job_id() -> None:
    payload = {
        "functions": [
            {"type": "EI", "name": "Login", "complexity": "low", "justification": ""}
        ],
        "vafFactors": [
            {"name": "Data communications", "value": 3, "rationale": ""}
        ],
    }
    respx.post(f"{OLLAMA_URL}/api/generate").mock(
        return_value=httpx.Response(200, json={"response": json.dumps(payload)})
    )

    zip_bytes = _zip_with([("src/login.py", b"def login(): pass\n")])
    with TestClient(app) as client:
        resp = client.post(
            "/analyze",
            files={"files": ("project.zip", zip_bytes, "application/zip")},
        )
        assert resp.status_code == 202
        job_id = resp.json()["jobId"]
        assert job_id

        # Poll until done (background task scheduled by /analyze).
        body = {"status": "pending"}
        for _ in range(50):
            r = client.get(f"/analyze/{job_id}")
            assert r.status_code == 200
            body = r.json()
            if body["status"] in ("done", "error"):
                break
            time.sleep(0.05)
        assert body["status"] == "done"
        assert body["summary"]["ufp"] == 3  # one EI low
        assert body["summary"]["vaf"] == 0.68  # 0.65 + 3/100
