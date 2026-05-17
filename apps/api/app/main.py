"""FastAPI entrypoint."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from app.config import Settings, get_settings
from app.fpa import AnalysisResult, compute_analysis
from app.ingest import (
    IngestError,
    ZipBombError,
    ZipSlipError,
    ingest_uploads,
)
from app.jobs import Job, JobEvent, JobStore
from app.llm import OllamaClient, OllamaError, OllamaInvalidResponse, build_prompt
from app.llm.prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def _build_ollama_client(settings: Settings) -> OllamaClient:
    return OllamaClient(
        base_url=settings.ollama_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
        max_retries=settings.ollama_max_retries,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.settings = settings
    app.state.jobs = JobStore(ttl_seconds=settings.job_ttl_seconds)
    app.state.ollama = _build_ollama_client(settings)
    try:
        yield
    finally:
        await app.state.ollama.close()


app = FastAPI(title="FPA API", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def _attach_cors(request, call_next):  # pragma: no cover - thin glue
    return await call_next(request)


def _settings_dep() -> Settings:
    return get_settings()


def _setup_cors(app: FastAPI, settings: Settings) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        allow_credentials=False,
    )


_setup_cors(app, get_settings())


@app.get("/healthz")
async def healthz() -> dict[str, object]:
    ollama_ok = False
    if hasattr(app.state, "ollama"):
        try:
            ollama_ok = await app.state.ollama.health()
        except Exception:
            ollama_ok = False
    return {"ok": True, "ollama": ollama_ok}


_UPLOAD_CHUNK_BYTES = 1024 * 1024  # 1 MB


async def _read_upload_capped(upload: UploadFile, remaining: int) -> bytes:
    """Stream an upload in chunks, aborting once ``remaining`` bytes are exceeded.

    Prevents fully buffering a hostile multi-hundred-MB body before the size
    check fires. The Uvicorn/ASGI layer should also be started with
    ``--limit-max-request-body-size`` as defense in depth.
    """
    buf = bytearray()
    while True:
        chunk = await upload.read(_UPLOAD_CHUNK_BYTES)
        if not chunk:
            break
        if len(chunk) > remaining - len(buf):
            raise HTTPException(
                status_code=413,
                detail="upload exceeds max allowed bytes",
            )
        buf.extend(chunk)
    return bytes(buf)


@app.post("/analyze", status_code=status.HTTP_202_ACCEPTED)
async def analyze(
    files: list[UploadFile] = File(...),
    settings: Settings = Depends(_settings_dep),
) -> dict[str, str]:
    if not files:
        raise HTTPException(status_code=400, detail="no files uploaded")

    max_bytes = settings.max_upload_bytes
    total = 0
    payloads: list[tuple[str, bytes]] = []
    for upload in files:
        raw = await _read_upload_capped(upload, max_bytes - total)
        total += len(raw)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"upload exceeds {max_bytes} bytes",
            )
        payloads.append((upload.filename or "upload.bin", raw))

    try:
        files_extracted = ingest_uploads(
            payloads,
            max_decompressed_bytes=settings.max_decompressed_bytes,
            max_files=settings.max_archive_files,
            max_text_chars_per_file=settings.max_text_chars_per_file,
        )
    except (ZipSlipError, ZipBombError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IngestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not files_extracted:
        raise HTTPException(
            status_code=400,
            detail="no analyzable text content found in upload",
        )

    job = await app.state.jobs.create()
    asyncio.create_task(_run_job(job.id, files_extracted))
    return {"jobId": job.id}


async def _run_job(job_id: str, files_extracted) -> None:
    store: JobStore = app.state.jobs
    ollama: OllamaClient = app.state.ollama
    try:
        await store.update_status(
            job_id, "running", message="building prompt", progress=0.1
        )
        prompt = build_prompt(files_extracted)
        await store.update_status(
            job_id, "running", message="calling ollama", progress=0.3
        )
        analysis = await ollama.analyze(
            system_prompt=SYSTEM_PROMPT, user_prompt=prompt
        )
        await store.update_status(
            job_id, "running", message="computing FP", progress=0.8
        )
        result = compute_analysis(job_id, analysis)
        await store.update_status(
            job_id, "done", message="ok", progress=1.0, result=result
        )
    except (OllamaError, OllamaInvalidResponse) as exc:
        logger.exception("job %s failed: ollama error", job_id)
        await store.update_status(
            job_id, "error", message=str(exc), error=str(exc)
        )
    except Exception as exc:  # noqa: BLE001 - surface anything to client
        logger.exception("job %s failed: unexpected", job_id)
        await store.update_status(
            job_id, "error", message=str(exc), error=str(exc)
        )


@app.get("/analyze/{job_id}", response_model=AnalysisResult)
async def get_job(job_id: str) -> AnalysisResult:
    job: Job | None = await app.state.jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.result is not None:
        return job.result
    return AnalysisResult(jobId=job.id, status=job.status, error=job.error)


@app.get("/analyze/{job_id}/stream")
async def stream_job(job_id: str) -> EventSourceResponse:
    job: Job | None = await app.state.jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    async def event_gen():
        # Replay current state once on connect.
        yield {
            "event": "status",
            "data": JobEvent(
                status=job.status,
                message="connected",
                progress=1.0 if job.status == "done" else 0.0,
            ).__dict__,
        }
        if job.status in ("done", "error"):
            return
        while True:
            ev = await job.queue.get()
            yield {"event": "status", "data": ev.__dict__}
            if ev.status in ("done", "error"):
                break

    return EventSourceResponse(event_gen())


@app.exception_handler(IngestError)
async def _ingest_error_handler(_request, exc: IngestError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})
