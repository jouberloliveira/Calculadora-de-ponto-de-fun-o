# Architecture — Calculadora de Ponto de Função

## Goal

Public, no-auth web app that ingests a project (uploaded files) and returns a structured IFPUG Function Point analysis produced by a local LLM (Ollama).

## High-Level Flow

```
Browser ──(multipart upload)──► API (/analyze)
                                 │
                                 ├─► extract + sanitize files
                                 ├─► build LLM prompt (context windowed)
                                 ├─► POST http://localhost:11434/api/generate (Ollama)
                                 ├─► parse JSON response, validate with Pydantic
                                 └─► return FPA result
                                              │
Browser ◄────────(JSON FPA result)────────────┘
```

## Components

### `apps/web` (Next.js 14, App Router)
- `/` — landing + upload component (drag-and-drop, multiple files, MIME + size guard).
- `/analyze/[jobId]` — progress feedback (SSE or polling) and results render.
- Components: `UploadDropzone`, `JobProgress`, `FPAResultCard`, `FunctionBreakdownTable`.
- State: React Query for server state; no global store needed.
- Styling: Tailwind + shadcn/ui primitives.

### `apps/api` (FastAPI)
- `POST /analyze` — multipart upload, returns `jobId`.
- `GET /analyze/{jobId}` — poll status.
- `GET /analyze/{jobId}/stream` — SSE stream of progress events.
- `GET /healthz` — liveness.

Internal modules:
- `app/ingest/` — archive extraction (`zipfile`, with path traversal guards), file type detection, PDF→text (`pdfminer.six`).
- `app/llm/ollama.py` — Ollama client wrapper, prompt builder, retry on JSON parse failure.
- `app/fpa/` — IFPUG rules, Pydantic models, post-LLM validation + UFP/VAF/AFP computation.
- `app/jobs/` — in-memory job store (single-process MVP); swap to Redis later.

## Data Contract (FPA Result)

```json
{
  "jobId": "uuid",
  "status": "done",
  "summary": {
    "ufp": 158,
    "vaf": 1.05,
    "afp": 165.9
  },
  "functions": [
    {
      "type": "EI" | "EO" | "EQ" | "ILF" | "EIF",
      "name": "Create User",
      "complexity": "low" | "medium" | "high",
      "fp": 4,
      "justification": "..."
    }
  ],
  "vafFactors": [
    { "name": "Data communications", "value": 3, "rationale": "..." }
  ]
}
```

## Ollama Prompt Strategy

- System prompt instructs the model to act as an IFPUG-certified counter and respond ONLY in JSON matching the contract.
- Few-shot example with one EI + one ILF.
- Project context concatenated up to context window budget; chunked when exceeded (map-reduce summarization).
- Default model: `llama3:8b`. Configurable via `OLLAMA_MODEL` env var.

## Security / Threat Model (initial)

| Threat                          | Mitigation                                                |
|--------------------------------|-----------------------------------------------------------|
| Zip slip / path traversal      | Resolve real path, reject if outside extraction dir       |
| Zip bomb                       | Cap decompressed size (e.g., 100 MB), cap file count      |
| Malicious binary execution     | Never execute uploaded content; text-only ingestion       |
| LLM prompt injection           | Strip instructions from extracted text; output schema validation |
| DoS via large upload           | Request size limit (50 MB), per-IP rate limit             |
| PII leakage                    | No persistence; files purged after analysis               |

Full review owned by Security Reviewer.

## Environments

- `OLLAMA_URL=http://localhost:11434`
- `OLLAMA_MODEL=llama3`
- `MAX_UPLOAD_BYTES=52428800`
- `JOB_TTL_SECONDS=3600`

## Deployment (out of MVP scope)

Docker Compose with three services (`web`, `api`, `ollama`). Documented in a follow-up issue.
