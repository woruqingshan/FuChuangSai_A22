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
from services.storage import redis_store


BEIJING_TZ = timezone(timedelta(hours=8))
JobStatus = Literal["queued", "processing", "rendering", "completed", "failed", "cancelled"]
ACTIVE_STATUSES = {"queued", "processing", "rendering"}
TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


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
        self._redis = redis_store.client
        self._wake_event = asyncio.Event()
        self._worker_task: asyncio.Task | None = None
        self._monitor_tasks: dict[str, asyncio.Task] = {}
        self._stopping = False

    async def start(self) -> None:
        if self._worker_task and not self._worker_task.done():
            return
        self._stopping = False
        self._recover_jobs_after_restart()
        self._worker_task = asyncio.create_task(self._worker_loop(), name="a22-job-worker")
        self._wake_event.set()

    async def stop(self) -> None:
        self._stopping = True
        self._wake_event.set()
        for task in list(self._monitor_tasks.values()):
            task.cancel()
        if self._worker_task:
            await self._worker_task

    async def submit(self, *, session_id: str, turn_id: int, request: RemoteChatRequest) -> JobRecord:
        job_id = self._generate_job_id()
        created_at = datetime.now(UTC)
        lock = self._redis.lock(redis_store.key("jobs", "admission-lock"), timeout=5, blocking_timeout=5)
        with lock:
            session_marker_key = self._session_active_key(session_id)
            active_for_session = self._redis.get(session_marker_key)
            if active_for_session:
                raise JobError(
                    "A generation is already active for this session.",
                    status_code=409,
                    job_id=str(active_for_session),
                )
            capacity = int(self._redis.scard(self._nonterminal_key()))
            if capacity >= 1 + settings.job_queue_max_pending:
                raise JobError("Public generation queue is full.", status_code=429)

            job = JobRecord(
                job_id=job_id,
                session_id=session_id,
                turn_id=turn_id,
                request=request,
                status="queued",
                created_at=created_at,
            )
            pipe = self._redis.pipeline()
            pipe.hset(self._job_key(job_id), mapping=self._serialize_job(job))
            pipe.sadd(self._nonterminal_key(), job_id)
            pipe.set(session_marker_key, job_id)
            pipe.rpush(self._queue_key(), job_id)
            pipe.execute()

        self._wake_event.set()
        return job

    async def get(self, job_id: str) -> JobRecord | None:
        return self._load_job(job_id)

    async def queue_position(self, job_id: str) -> int | None:
        queued_ids = [str(item) for item in self._redis.lrange(self._queue_key(), 0, -1)]
        try:
            return queued_ids.index(job_id) + 1
        except ValueError:
            return None

    def is_terminal(self, status: str) -> bool:
        return status in TERMINAL_STATUSES

    async def _worker_loop(self) -> None:
        while not self._stopping:
            await self._wake_event.wait()
            self._wake_event.clear()
            while not self._stopping:
                job = await self._claim_next_job()
                if not job:
                    break
                await self._run_job(job)

    async def _claim_next_job(self) -> JobRecord | None:
        if self._redis.get(self._active_key()):
            return None
        job_id = self._redis.lpop(self._queue_key())
        if not job_id:
            return None
        job_id = str(job_id)
        job = self._load_job(job_id)
        if not job or job.status != "queued":
            return None
        if not self._redis.set(self._active_key(), job_id, nx=True):
            self._redis.lpush(self._queue_key(), job_id)
            return None
        job.status = "processing"
        job.started_at = datetime.now(UTC)
        self._save_job(job)
        return job

    async def _run_job(self, job: JobRecord) -> None:
        request_id = uuid4().hex[:12]
        try:
            response = await orchestrator_client.send_chat(job.request, request_id=request_id)
            if hasattr(response, "model_copy"):
                response = response.model_copy(update={"input_mode": job.request.input_type})
            else:
                response = response.copy(update={"input_mode": job.request.input_type})
            job.chat_response = response
            if response.reply_video_stream_url:
                job.status = "rendering"
                self._save_job(job)
                await self._wait_for_manifest_complete(job, response.reply_video_stream_url)
            else:
                self._finish_job(job, status="completed")
        except RemoteServiceError as exc:
            self._finish_job(job, status="failed", error=exc.detail)
        except Exception as exc:  # noqa: BLE001
            self._finish_job(job, status="failed", error=f"Generation job failed: {exc}")

    async def _wait_for_manifest_complete(self, job: JobRecord, manifest_url: str) -> None:
        deadline = datetime.now(UTC) + timedelta(seconds=settings.job_render_timeout_seconds)
        manifest_path = self._manifest_path(manifest_url)
        timeout = httpx.Timeout(settings.media_connect_timeout_seconds, read=settings.media_manifest_timeout_seconds)
        last_error = ""
        while datetime.now(UTC) < deadline and not self._stopping:
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
                if error:
                    self._finish_job(job, status="failed", error=str(error))
                elif chunks:
                    self._finish_job(job, status="completed")
                else:
                    self._finish_job(job, status="failed", error="Digital human video render produced no chunks.")
                return

            await asyncio.sleep(settings.job_manifest_poll_seconds)

        if not self._stopping:
            timeout_error = "Digital human video render timed out."
            self._finish_job(job, status="failed", error=last_error or timeout_error)

    def _recover_jobs_after_restart(self) -> None:
        self._redis.delete(self._active_key())
        for key in self._redis.scan_iter(match=redis_store.key("job", "*")):
            job_id = str(key).rsplit(":", 1)[-1]
            job = self._load_job(job_id)
            if not job:
                continue
            if job.status == "processing":
                self._finish_job(job, status="failed", error="edge_restarted_during_processing")
                continue
            if job.status == "rendering":
                if job.chat_response and job.chat_response.reply_video_stream_url:
                    self._redis.set(self._active_key(), job.job_id)
                    self._monitor_tasks[job.job_id] = asyncio.create_task(
                        self._resume_rendering_job(job),
                        name=f"a22-job-monitor-{job.job_id}",
                    )
                else:
                    self._finish_job(job, status="failed", error="edge_restarted_without_render_manifest")
        self._wake_event.set()

    async def _resume_rendering_job(self, job: JobRecord) -> None:
        if not job.chat_response or not job.chat_response.reply_video_stream_url:
            self._finish_job(job, status="failed", error="edge_restarted_without_render_manifest")
            return
        try:
            await self._wait_for_manifest_complete(job, job.chat_response.reply_video_stream_url)
        finally:
            self._monitor_tasks.pop(job.job_id, None)
            self._wake_event.set()

    def _finish_job(self, job: JobRecord, *, status: JobStatus, error: str | None = None) -> None:
        job.status = status
        job.error = error
        job.completed_at = datetime.now(UTC)
        self._save_job(job, terminal=True)
        pipe = self._redis.pipeline()
        pipe.srem(self._nonterminal_key(), job.job_id)
        pipe.delete(self._session_active_key(job.session_id))
        pipe.lrem(self._queue_key(), 0, job.job_id)
        if self._redis.get(self._active_key()) == job.job_id:
            pipe.delete(self._active_key())
        pipe.expire(self._job_key(job.job_id), settings.job_retention_seconds)
        pipe.execute()
        self._wake_event.set()

    def _save_job(self, job: JobRecord, *, terminal: bool = False) -> None:
        key = self._job_key(job.job_id)
        self._redis.hset(key, mapping=self._serialize_job(job))
        if terminal:
            self._redis.expire(key, settings.job_retention_seconds)

    def _load_job(self, job_id: str) -> JobRecord | None:
        payload = self._redis.hgetall(self._job_key(job_id))
        if not payload:
            return None
        request = self._parse_model(RemoteChatRequest, str(payload["request_json"]))
        chat_response_json = payload.get("chat_response_json")
        chat_response = self._parse_model(ChatResponse, str(chat_response_json)) if chat_response_json else None
        return JobRecord(
            job_id=str(payload["job_id"]),
            session_id=str(payload["session_id"]),
            turn_id=int(payload["turn_id"]),
            request=request,
            status=str(payload["status"]),  # type: ignore[arg-type]
            created_at=self._parse_dt(str(payload["created_at"])),
            started_at=self._parse_optional_dt(payload.get("started_at")),
            completed_at=self._parse_optional_dt(payload.get("completed_at")),
            error=payload.get("error") or None,
            chat_response=chat_response,
        )

    def _serialize_job(self, job: JobRecord) -> dict[str, str]:
        return {
            "job_id": job.job_id,
            "session_id": job.session_id,
            "turn_id": str(job.turn_id),
            "request_json": self._model_to_json(job.request),
            "status": job.status,
            "created_at": self._serialize_dt(job.created_at),
            "started_at": self._serialize_optional_dt(job.started_at),
            "completed_at": self._serialize_optional_dt(job.completed_at),
            "error": job.error or "",
            "chat_response_json": self._model_to_json(job.chat_response) if job.chat_response else "",
        }

    @staticmethod
    def _manifest_path(manifest_url: str) -> str:
        if manifest_url.startswith("http://") or manifest_url.startswith("https://"):
            parsed = httpx.URL(manifest_url)
            path = parsed.raw_path.decode("utf-8")
            query = parsed.query.decode("utf-8") if isinstance(parsed.query, bytes) else str(parsed.query)
            return f"{path}?{query}" if query else path
        return manifest_url if manifest_url.startswith("/") else f"/{manifest_url}"

    @staticmethod
    def _model_to_json(model) -> str:
        if hasattr(model, "model_dump_json"):
            return model.model_dump_json()
        return model.json()

    @staticmethod
    def _parse_model(model_class, payload: str):
        if hasattr(model_class, "model_validate_json"):
            return model_class.model_validate_json(payload)
        return model_class.parse_raw(payload)

    @staticmethod
    def _serialize_dt(value: datetime) -> str:
        return value.astimezone(UTC).isoformat()

    @staticmethod
    def _serialize_optional_dt(value: datetime | None) -> str:
        return value.astimezone(UTC).isoformat() if value else ""

    @staticmethod
    def _parse_dt(value: str) -> datetime:
        return datetime.fromisoformat(value).astimezone(UTC)

    @classmethod
    def _parse_optional_dt(cls, value: str | None) -> datetime | None:
        return cls._parse_dt(value) if value else None

    def _job_key(self, job_id: str) -> str:
        return redis_store.key("job", job_id)

    def _queue_key(self) -> str:
        return redis_store.key("jobs", "queue")

    def _active_key(self) -> str:
        return redis_store.key("jobs", "active")

    def _nonterminal_key(self) -> str:
        return redis_store.key("jobs", "nonterminal")

    def _session_active_key(self, session_id: str) -> str:
        return redis_store.key("jobs", "session-active", session_id)

    @staticmethod
    def _generate_job_id() -> str:
        timestamp = datetime.now(UTC).astimezone(BEIJING_TZ).strftime("%Y%m%dT%H%M%SCST")
        return f"job_{timestamp}_{secrets.token_hex(12)}"


job_manager = JobManager()
