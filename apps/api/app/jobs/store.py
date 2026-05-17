"""In-memory job store.

Single-process MVP. Thread/async safety via an ``asyncio.Lock``. Each job
holds a result, a progress event queue (for SSE), and a TTL after which
finished jobs are evicted.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Literal

from app.fpa.models import AnalysisResult

JobStatus = Literal["pending", "running", "done", "error"]


@dataclass
class JobEvent:
    status: JobStatus
    message: str = ""
    progress: float = 0.0  # 0..1


@dataclass
class Job:
    id: str
    status: JobStatus = "pending"
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    result: AnalysisResult | None = None
    error: str | None = None
    queue: asyncio.Queue[JobEvent] = field(default_factory=asyncio.Queue)


class JobStore:
    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = asyncio.Lock()
        self._ttl = ttl_seconds

    async def create(self) -> Job:
        async with self._lock:
            self._evict_expired_locked()
            job_id = str(uuid.uuid4())
            job = Job(id=job_id)
            self._jobs[job_id] = job
            return job

    async def get(self, job_id: str) -> Job | None:
        async with self._lock:
            self._evict_expired_locked()
            return self._jobs.get(job_id)

    async def update_status(
        self,
        job_id: str,
        status: JobStatus,
        *,
        message: str = "",
        progress: float = 0.0,
        result: AnalysisResult | None = None,
        error: str | None = None,
    ) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = status
            if result is not None:
                job.result = result
            if error is not None:
                job.error = error
            if status in ("done", "error"):
                job.finished_at = time.time()
        # publish event outside the lock to avoid blocking subscribers
        await job.queue.put(JobEvent(status=status, message=message, progress=progress))

    def _evict_expired_locked(self) -> None:
        now = time.time()
        expired = [
            jid
            for jid, job in self._jobs.items()
            if job.finished_at is not None and (now - job.finished_at) > self._ttl
        ]
        for jid in expired:
            self._jobs.pop(jid, None)
