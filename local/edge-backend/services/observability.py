import sys
import time
from pathlib import Path

SHARED_PATH_CANDIDATES = [
    Path("/shared"),
    Path(__file__).resolve().parents[3] / "shared" if len(Path(__file__).resolve().parents) > 3 else None,
]

for candidate in SHARED_PATH_CANDIDATES:
    if candidate and candidate.exists() and str(candidate) not in sys.path:
        sys.path.append(str(candidate))

from observability import JsonlRunLogger, build_run_id  # noqa: E402

from config import settings


class EdgeObservability:
    def __init__(self) -> None:
        self.service_name = "edge-backend"
        self.run_id = build_run_id(self.service_name)
        self.started_at = time.perf_counter()
        self._events_logger = JsonlRunLogger(
            service_name=self.service_name,
            log_dir=settings.log_dir,
            channel="events",
            run_id=self.run_id,
        )
        self._bridge_logger = JsonlRunLogger(
            service_name=self.service_name,
            log_dir=settings.log_dir,
            channel="bridge",
            run_id=self.run_id,
        )

    def log_run_start(self) -> None:
        self._events_logger.emit(
            "run_start",
            {
                "cloud_api_base": settings.cloud_api_base,
                "request_timeout_seconds": settings.request_timeout_seconds,
                "local_asr_provider": settings.local_asr_provider,
                "local_asr_model": settings.local_asr_model,
                "local_asr_model_path": settings.local_asr_model_path,
                "local_asr_language": settings.local_asr_language,
                "local_asr_device": settings.local_asr_device,
                "local_asr_warmup_enabled": settings.local_asr_warmup_enabled,
                "log_dir": settings.log_dir,
            },
        )

    def log_run_stop(self) -> None:
        self._events_logger.emit(
            "run_stop",
            {
                "uptime_seconds": round(time.perf_counter() - self.started_at, 3),
            },
        )

    def log_chat_request_received(self, request_id: str, payload: dict) -> None:
        self._events_logger.emit(
            "chat_request_received",
            {
                "request_id": request_id,
                **payload,
            },
        )

    def log_chat_request_prepared(self, request_id: str, payload: dict) -> None:
        self._events_logger.emit(
            "chat_request_prepared",
            {
                "request_id": request_id,
                **payload,
            },
        )

    def log_asr_provider_error(
        self,
        request_id: str,
        *,
        provider: str,
        detail: str,
        error_type: str,
        latency_ms: int,
        payload: dict,
    ) -> None:
        self._events_logger.emit(
            "asr_provider_error",
            {
                "request_id": request_id,
                "provider": provider,
                "error_type": error_type,
                "detail": detail,
                "latency_ms": latency_ms,
                **payload,
            },
        )

    def log_asr_transcription(
        self,
        request_id: str,
        *,
        provider: str,
        source: str,
        confidence: float | None,
        latency_ms: int,
        payload: dict,
    ) -> None:
        self._events_logger.emit(
            "asr_transcription",
            {
                "request_id": request_id,
                "provider": provider,
                "source": source,
                "confidence": confidence,
                "latency_ms": latency_ms,
                **payload,
            },
        )

    def log_asr_warmup_start(self, *, provider: str, payload: dict) -> None:
        self._events_logger.emit(
            "asr_warmup_start",
            {
                "provider": provider,
                **payload,
            },
        )

    def log_asr_warmup_ready(self, *, provider: str, latency_ms: int, payload: dict) -> None:
        self._events_logger.emit(
            "asr_warmup_ready",
            {
                "provider": provider,
                "latency_ms": latency_ms,
                **payload,
            },
        )

    def log_asr_warmup_error(
        self,
        *,
        provider: str,
        detail: str,
        error_type: str,
        latency_ms: int,
        payload: dict,
    ) -> None:
        self._events_logger.emit(
            "asr_warmup_error",
            {
                "provider": provider,
                "error_type": error_type,
                "detail": detail,
                "latency_ms": latency_ms,
                **payload,
            },
        )

    def log_bridge_outbound(self, request_id: str, url: str, payload: dict) -> None:
        self._bridge_logger.emit(
            "bridge_outbound",
            {
                "request_id": request_id,
                "url": url,
                "payload": payload,
            },
        )

    def log_bridge_inbound(self, request_id: str, status_code: int, latency_ms: int, payload: dict) -> None:
        self._bridge_logger.emit(
            "bridge_inbound",
            {
                "request_id": request_id,
                "status_code": status_code,
                "latency_ms": latency_ms,
                "payload": payload,
            },
        )

    def log_bridge_error(self, request_id: str, latency_ms: int, detail: str, status_code: int, payload: dict) -> None:
        self._bridge_logger.emit(
            "bridge_error",
            {
                "request_id": request_id,
                "status_code": status_code,
                "latency_ms": latency_ms,
                "detail": detail,
                "payload": payload,
            },
        )

    def log_chat_response(self, request_id: str, latency_ms: int, payload: dict) -> None:
        self._events_logger.emit(
            "chat_response",
            {
                "request_id": request_id,
                "latency_ms": latency_ms,
                **payload,
            },
        )

    def log_chat_error(self, request_id: str, latency_ms: int, detail: str, status_code: int) -> None:
        self._events_logger.emit(
            "chat_error",
            {
                "request_id": request_id,
                "latency_ms": latency_ms,
                "detail": detail,
                "status_code": status_code,
            },
        )


edge_observability = EdgeObservability()
