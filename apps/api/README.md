# apps/api

FastAPI service that ingests project files, prompts Ollama, and returns an IFPUG Function Point analysis.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000 --limit-max-request-body-size 55000000
```

The `--limit-max-request-body-size` flag enforces the upload cap at the ASGI
layer so hostile clients cannot make the process buffer hundreds of megabytes
before the in-app size check fires. Keep it slightly above `MAX_UPLOAD_BYTES`
to allow for multipart envelope overhead. The application also streams uploads
in chunks and aborts once `MAX_UPLOAD_BYTES` is exceeded.

Make sure Ollama is running locally:

```bash
ollama serve
ollama pull llama3
```

## Configuration

| Env var            | Default                     | Description                              |
|--------------------|-----------------------------|------------------------------------------|
| `OLLAMA_URL`       | `http://localhost:11434`    | Base URL of Ollama daemon                |
| `OLLAMA_MODEL`     | `llama3`                    | Model name                               |
| `MAX_UPLOAD_BYTES` | `52428800` (50 MB)          | Max total upload size                    |
| `JOB_TTL_SECONDS`  | `3600`                      | TTL for finished jobs                    |
| `CORS_ORIGINS`     | `http://localhost:3000`     | Comma-separated allowed CORS origins     |

## Endpoints

- `POST /analyze` — multipart upload (`files[]`), returns `{ "jobId": "..." }`.
- `GET /analyze/{jobId}` — current status and result if `done`.
- `GET /analyze/{jobId}/stream` — SSE progress events.
- `GET /healthz` — `{ "ok": true, "ollama": bool }`.

## Tests

```bash
pytest
```
