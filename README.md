# Calculadora de Ponto de Função

Web application that analyzes project files (ZIP, PDF, source code, docs) using a local LLM (Ollama) to compute IFPUG Function Point metrics.

## Architecture

Monorepo with two apps:

- `apps/api` — FastAPI service. Accepts uploads, extracts archives, prompts Ollama, returns structured FPA result.
- `apps/web` — Next.js (App Router) frontend. Upload UI, progress feedback, detailed results view.

See `docs/ARCHITECTURE.md` for component diagram, data contracts, and threat model.

## Stack

| Layer    | Tech                            |
|----------|---------------------------------|
| Frontend | Next.js 14, React 18, Tailwind  |
| Backend  | FastAPI (Python 3.11), Pydantic |
| LLM      | Ollama (`llama3` or `qwen2.5`)  |
| Tests    | Pytest (api), Vitest (web)      |

## Function Point Metrics Returned

- External Inputs (EI)
- External Outputs (EO)
- External Inquiries (EQ)
- Internal Logical Files (ILF)
- External Interface Files (EIF)
- Complexity per function (low/medium/high)
- Unadjusted Function Points (UFP)
- Value Adjustment Factor (VAF)
- Adjusted Function Points (AFP)

## Local Development

```bash
# Backend
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd apps/web
npm install
npm run dev

# Ollama
ollama serve
ollama pull llama3
```

## Branch Strategy

- `main` — production
- `dev` — integration
- `feat/<name>`, `fix/<name>`, `chore/<name>`

PRs target `dev`, require 1 approval (CTO or Security), CI green before merge.
