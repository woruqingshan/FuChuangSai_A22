import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
import secrets
from typing import Literal
from uuid import uuid4

import httpx

from config import settings
from models import ChatResponse, RemoteChatRequest
from services.orchestrator_client import RemoteServiceError, orchestrator_client


BEIJING_TZ = timezone(timedelta(hours=8))
JobStatus = Literal["queued", "processing", "rendering", "completed", "failed", "cancelled"]


class JobError(Exception):
    def __init__(self, detail: str, status_code: int = 400, *, job_id: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.job_id = job_id


@dataclass
class JobRecord:
    job_id: str
    session_id: str
    turn_id: int
    request: RemoteChatRequest
    status: JobStatus
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    chat_response: ChatResponse | None = None


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._queue: list[str] = []
        self._active_job_id: str | None = None
        self._lock = asyncio.Lock()
        self._wake_event = asyncio.Event()
        self._worker_task: asyncio.Task | None = None
        self._stopping = False

    async def start(self) -> None:
        if self._worker_task and not self._worker_task.done():
            return
        self._stopping = False
        self._worker_task = asyncio.create_task(self._worker_loop(), name="a22-job-worker")

    async def stop(self) -> None:
        self._stopping = True
        self._wake_event.set()
        if self._worker_task:
            await self._worker_task

    async def submit(self, *, session_id: str, turn_id: int, request: RemoteChatRequest) -> JobRecord:
        async with self._lock:
            self._cleanup_locked(now=datetime.now(UTC))
            active_job = self._find_active_job_for_session_locked(session_id)
            if active_job:
                raise JobError(
                    "A generation is already active for this session.",
                    status_code=409,
                    job_id=active_job.job_id,
                )
            if self._active_capacity_count_locked() >= 1 + settings.job_queue_max_pending:
                raise JobError("Public generation queue is full.", status_code=429)

            job = JobRecord(
                job_id=self._generate_job_id(),
                session_id=session_id,
                turn_id=turn_id,
                request=request,
                status="queued",
                created_at=datetime.now(UTC),
            )
            self._jobs[job.job_id] = job
            self._queue.append(job.job_id)
            self._wake_event.set()
            return job

    async def get(self, job_id: str) -> JobRecord | None:
        async with self._lock:
            self._cleanup_locked(now=datetime.now(UTC))
            return self._jobs.get(job_id)

    async def queue_position(self, job_id: str) -> int | None:
        async with self._lock:
            return self._queue_position_locked(job_id)

    def is_terminal(self, status: str) -> bool:
        return status in {"completed", "failed", "cancelled"}

    async def _worker_loop(self) -> None:
        while not self._stopping:
            await self._wake_event.wait()
            self._wake_event.clear()
            while not self._stopping:
                job = await self._claim_next_job()
                if not job:
                    break
                await self._run_job(job)
                async with self._lock:
                    if self._active_job_id == job.job_id:
                        self._active_job_id = None
                    self._cleanup_locked(now=datetime.now(UTC))

    async def _claim_next_job(self) -> JobRecord | None:
        async with self._lock:
            if self._active_job_id or not self._queue:
                return None
            job_id = self._queue.pop(0)
            job = self._jobs.get(job_id)
            if not job or job.status != "queued":
                return None
            self._active_job_id = job_id
            job.status = "processing"
            job.started_at = datetime.now(UTC)
            return job

    async def _run_job(self, job: JobRecord) -> None:
        request_id = uuid4().hex[:12]
        try:
            response = await orchestrator_client.send_chat(job.request, request_id=request_id)
            if hasattr(response, "model_copy"):
                response = response.model_copy(update={"input_mode": job.request.input_type})
            else:
                response = response.copy(update={"input_mode": job.request.input_type})
            async with self._lock:
                job.chat_response = response
                if response.reply_video_stream_url:
                    job.status = "rendering"
                else:
                    self._finish_job_locked(job, status="completed")

            if response.reply_video_stream_url:
                await self._wait_for_manifest_complete(job, response.reply_video_stream_url)
        except RemoteServiceError as exc:
            async with self._lock:
                self._finish_job_locked(job, status="failed", error=exc.detail)
        except Exception as exc:  # noqa: BLE001
            async with self._lock:
                self._finish_job_locked(job, status="failed", error=f"Generation job failed: {exc}")

    async def _wait_for_manifest_complete(self, job: JobRecord, manifest_url: str) -> None:
        deadline = datetime.now(UTC) + timedelta(seconds=settings.job_render_timeout_seconds)
        manifest_path = self._manifest_path(manifest_url)
        timeout = httpx.Timeout(settings.media_connect_timeout_seconds, read=settings.media_manifest_timeout_seconds)
        while datetime.now(UTC) < deadline:
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(f"{settings.cloud_api_base}{manifest_path}")
                    response.raise_for_status()
                    payload = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                await asyncio.sleep(settings.job_manifest_poll_seconds)
                last_error = str(exc)
                continue

            if payload.get("complete") is True:
                error = payload.get("error")
                chunks = payload.get("chunks") or []
                async with self._lock:
                    if error:
                        self._finish_job_locked(job, status="failed", error=str(error))
                    elif chunks:
                        self._finish_job_locked(job, status="completed")
                    else:
                        self._finish_job_locked(job, status="failed", error="Digital human video render produced no chunks.")
                return

            await asyncio.sleep(settings.job_manifest_poll_seconds)

        async with self._lock:
            self._finish_job_locked(job, status="failed", error="Digital human video render timed out.")

    @staticmethod
    def _manifest_path(manifest_url: str) -> str:
        if manifest_url.startswith("http://") or manifest_url.startswith("https://"):
            parsed = httpx.URL(manifest_url)
            path = parsed.raw_path.decode("utf-8")
            query = parsed.query.decode("utf-8") if isinstance(parsed.query, bytes) else str(parsed.query)
            return f"{path}?{query}" if query else path
        return manifest_url if manifest_url.startswith("/") else f"/{manifest_url}"

    def _finish_job_locked(self, job: JobRecord, *, status: JobStatus, error: str | None = None) -> None:
        job.status = status
        job.error = error
        job.completed_at = datetime.now(UTC)

    def _find_active_job_for_session_locked(self, session_id: str) -> JobRecord | None:
        for job in self._jobs.values():
            if job.session_id == session_id and job.status in {"queued", "processing", "rendering"}:
                return job
        return None

    def _active_capacity_count_locked(self) -> int:
        return sum(1 for job in self._jobs.values() if job.status in {"queued", "processing", "rendering"})

    def _queue_position_locked(self, job_id: str) -> int | None:
        try:
            return self._queue.index(job_id) + 1
        except ValueError:
            return None

    def _cleanup_locked(self, *, now: datetime) -> None:
        cutoff = now - timedelta(seconds=settings.job_retention_seconds)
        removable_job_ids = [
            job_id
            for job_id, job in self._jobs.items()
            if self.is_terminal(job.status) and job.completed_at and job.completed_at < cutoff
        ]
        for job_id in removable_job_ids:
            self._jobs.pop(job_id, None)
        self._queue = [job_id for job_id in self._queue if job_id in self._jobs]

    @staticmethod
    def _generate_job_id() -> str:
        timestamp = datetime.now(UTC).astimezone(BEIJING_TZ).strftime("%Y%m%dT%H%M%SCST")
        return f"job_{timestamp}_{secrets.token_hex(12)}"


job_manager = JobManager()
