import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Protocol

from config import settings
from services.audio.contracts import AudioMeta, TranscriptionResult
from services.audio.wav_utils import decode_wav_audio
from services.observability import edge_observability


class BaseSpeechRecognizer(Protocol):
    provider_name: str

    def transcribe(
        self,
        *,
        audio_bytes: bytes,
        audio_meta: AudioMeta,
        client_text_hint: str | None,
        client_text_source: str | None,
    ) -> TranscriptionResult:
        ...


class BrowserHintSpeechRecognizer:
    provider_name = "browser_hint"

    def transcribe(
        self,
        *,
        audio_bytes: bytes,
        audio_meta: AudioMeta,
        client_text_hint: str | None,
        client_text_source: str | None,
    ) -> TranscriptionResult:
        del audio_bytes, audio_meta

        if client_text_hint and client_text_hint.strip():
            return TranscriptionResult(
                text=client_text_hint.strip(),
                source=client_text_source or "browser_speech_api",
                confidence=0.65,
            )

        return TranscriptionResult(
            text="Audio input received from the local microphone.",
            source="audio_placeholder",
            confidence=0.15,
        )


class FasterWhisperSpeechRecognizer:
    provider_name = "faster_whisper"

    def __init__(self) -> None:
        self._model = None

    def transcribe(
        self,
        *,
        audio_bytes: bytes,
        audio_meta: AudioMeta,
        client_text_hint: str | None,
        client_text_source: str | None,
    ) -> TranscriptionResult:
        del client_text_hint, client_text_source

        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("faster_whisper is not installed in the local edge-backend environment.") from exc

        if self._model is None:
            self._model = WhisperModel(
                settings.local_asr_model,
                device=settings.local_asr_device,
                compute_type=settings.local_asr_compute_type,
            )

        suffix = f".{(audio_meta.format or 'wav').lower()}"
        with NamedTemporaryFile(suffix=suffix) as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio.flush()
            segments, info = self._model.transcribe(
                temp_audio.name,
                language=settings.local_asr_language or None,
                vad_filter=True,
            )
            text = " ".join(segment.text.strip() for segment in segments if segment.text.strip()).strip()

        if not text:
            return TranscriptionResult(
                text="Audio input received from the local microphone.",
                source="audio_placeholder",
                confidence=0.1,
            )

        probability = getattr(info, "language_probability", None)
        return TranscriptionResult(
            text=text,
            source="faster_whisper",
            confidence=round(probability, 4) if isinstance(probability, float) else None,
        )


class BelleWhisperSpeechRecognizer:
    provider_name = "belle_whisper"

    def __init__(self) -> None:
        self._pipeline = None

    def _resolve_model_ref(self) -> tuple[str, bool]:
        model_ref = settings.local_asr_model_path or settings.local_asr_model
        model_path = Path(model_ref)
        resolved_model_ref = str(model_path) if model_path.exists() else model_ref
        return resolved_model_ref, model_path.exists()

    def _generation_kwargs(self) -> dict[str, str]:
        return {
            "language": settings.local_asr_language,
            "task": "transcribe",
        }

    def _ensure_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline

        try:
            import torch
            from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "transformers and torch are required for the BELLE Whisper ASR provider."
            ) from exc

        resolved_model_ref, use_local_files_only = self._resolve_model_ref()
        device = settings.local_asr_device
        torch_dtype = torch.float16 if device.startswith("cuda") else torch.float32

        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            resolved_model_ref,
            torch_dtype=torch_dtype,
            low_cpu_mem_usage=True,
            use_safetensors=True,
            local_files_only=use_local_files_only,
        )
        model.to(device)

        processor = AutoProcessor.from_pretrained(
            resolved_model_ref,
            local_files_only=use_local_files_only,
        )

        self._pipeline = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            torch_dtype=torch_dtype,
            device=device,
        )
        self._pipeline.model.config.forced_decoder_ids = (
            self._pipeline.tokenizer.get_decoder_prompt_ids(
                language=settings.local_asr_language,
                task="transcribe",
            )
        )
        return self._pipeline

    def warmup(self) -> str:
        import numpy as np

        pipeline_instance = self._ensure_pipeline()
        result = pipeline_instance(
            {
                "raw": np.zeros(48000, dtype=np.float32),
                "sampling_rate": 48000,
            },
            generate_kwargs=self._generation_kwargs(),
        )
        if isinstance(result, dict):
            return str(result.get("text", "")).strip()
        if isinstance(result, str):
            return result.strip()
        return ""

    def transcribe(
        self,
        *,
        audio_bytes: bytes,
        audio_meta: AudioMeta,
        client_text_hint: str | None,
        client_text_source: str | None,
    ) -> TranscriptionResult:
        del client_text_hint, client_text_source

        try:
            import numpy as np
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "numpy is required for the BELLE Whisper ASR provider."
            ) from exc

        pipeline_instance = self._ensure_pipeline()

        if (audio_meta.format or "wav").lower() == "wav":
            decoded_audio = decode_wav_audio(audio_bytes)
            if decoded_audio.channels == 1:
                waveform = decoded_audio.samples_by_channel[0]
            else:
                waveform = [
                    sum(channel_samples) / decoded_audio.channels
                    for channel_samples in zip(*decoded_audio.samples_by_channel, strict=False)
                ]
            pipeline_input = {
                "raw": np.asarray(waveform, dtype=np.float32),
                "sampling_rate": decoded_audio.sample_rate_hz,
            }
            result = pipeline_instance(
                pipeline_input,
                generate_kwargs=self._generation_kwargs(),
            )
        else:
            suffix = f".{(audio_meta.format or 'wav').lower()}"
            with NamedTemporaryFile(suffix=suffix) as temp_audio:
                temp_audio.write(audio_bytes)
                temp_audio.flush()
                result = pipeline_instance(
                    temp_audio.name,
                    generate_kwargs=self._generation_kwargs(),
                )

        text = ""
        if isinstance(result, dict):
            text = str(result.get("text", "")).strip()
        elif isinstance(result, str):
            text = result.strip()

        if not text:
            return TranscriptionResult(
                text="Audio input received from the local microphone.",
                source="audio_placeholder",
                confidence=0.1,
            )

        return TranscriptionResult(
            text=text,
            source="belle_whisper",
            confidence=None,
        )


class FallbackSpeechRecognizer:
    provider_name = "fallback"

    def transcribe(
        self,
        *,
        audio_bytes: bytes,
        audio_meta: AudioMeta,
        client_text_hint: str | None,
        client_text_source: str | None,
    ) -> TranscriptionResult:
        del audio_bytes, audio_meta, client_text_source

        if client_text_hint and client_text_hint.strip():
            return TranscriptionResult(
                text=client_text_hint.strip(),
                source="browser_hint_fallback",
                confidence=0.5,
            )

        return TranscriptionResult(
            text="Audio input received from the local microphone.",
            source="audio_placeholder",
            confidence=0.1,
        )


class SpeechRecognitionService:
    def __init__(self) -> None:
        self._provider_name = settings.local_asr_provider
        self._provider = self._build_provider()
        self._fallback = FallbackSpeechRecognizer()

    def _build_provider(self) -> BaseSpeechRecognizer:
        if settings.local_asr_provider == "belle_whisper":
            return BelleWhisperSpeechRecognizer()

        if settings.local_asr_provider == "faster_whisper":
            return FasterWhisperSpeechRecognizer()

        if settings.local_asr_provider == "fallback":
            return FallbackSpeechRecognizer()

        return BrowserHintSpeechRecognizer()

    def warmup(self) -> None:
        if not settings.local_asr_warmup_enabled:
            return

        provider = self._provider
        warmup_callable = getattr(provider, "warmup", None)
        if not callable(warmup_callable):
            return

        started_at = time.perf_counter()
        model_ref = settings.local_asr_model_path or settings.local_asr_model
        edge_observability.log_asr_warmup_start(
            provider=provider.provider_name,
            payload={
                "model_ref": model_ref,
                "device": settings.local_asr_device,
            },
        )
        try:
            warmup_text = warmup_callable()
            edge_observability.log_asr_warmup_ready(
                provider=provider.provider_name,
                latency_ms=int((time.perf_counter() - started_at) * 1000),
                payload={
                    "model_ref": model_ref,
                    "device": settings.local_asr_device,
                    "recognized_text": warmup_text,
                    "recognized_text_length": len(warmup_text),
                },
            )
        except Exception as exc:  # noqa: BLE001
            edge_observability.log_asr_warmup_error(
                provider=provider.provider_name,
                detail=str(exc),
                error_type=type(exc).__name__,
                latency_ms=int((time.perf_counter() - started_at) * 1000),
                payload={
                    "model_ref": model_ref,
                    "device": settings.local_asr_device,
                },
            )

    def transcribe(
        self,
        *,
        audio_bytes: bytes,
        audio_meta: AudioMeta,
        client_text_hint: str | None,
        client_text_source: str | None,
        request_id: str | None = None,
    ) -> TranscriptionResult:
        started_at = time.perf_counter()
        model_ref = settings.local_asr_model_path or settings.local_asr_model

        try:
            result = self._provider.transcribe(
                audio_bytes=audio_bytes,
                audio_meta=audio_meta,
                client_text_hint=client_text_hint,
                client_text_source=client_text_source,
            )
            if request_id:
                edge_observability.log_asr_transcription(
                    request_id,
                    provider=self._provider.provider_name,
                    source=result.source,
                    confidence=result.confidence,
                    latency_ms=int((time.perf_counter() - started_at) * 1000),
                    payload={
                        "audio_format": audio_meta.format,
                        "audio_duration_ms": audio_meta.duration_ms,
                        "audio_sample_rate_hz": audio_meta.sample_rate_hz,
                        "audio_channels": audio_meta.channels,
                        "client_asr_text": client_text_hint,
                        "client_asr_source": client_text_source,
                        "recognized_text": result.text,
                        "recognized_text_length": len(result.text),
                        "model_ref": model_ref,
                        "device": settings.local_asr_device,
                        "fallback_used": False,
                    },
                )
            return result
        except Exception as exc:  # noqa: BLE001
            if request_id:
                edge_observability.log_asr_provider_error(
                    request_id,
                    provider=self._provider.provider_name,
                    detail=str(exc),
                    error_type=type(exc).__name__,
                    latency_ms=int((time.perf_counter() - started_at) * 1000),
                    payload={
                        "audio_format": audio_meta.format,
                        "audio_duration_ms": audio_meta.duration_ms,
                        "audio_sample_rate_hz": audio_meta.sample_rate_hz,
                        "audio_channels": audio_meta.channels,
                        "client_asr_text": client_text_hint,
                        "client_asr_source": client_text_source,
                        "model_ref": model_ref,
                        "device": settings.local_asr_device,
                    },
                )

            fallback_started_at = time.perf_counter()
            fallback_result = self._fallback.transcribe(
                audio_bytes=audio_bytes,
                audio_meta=audio_meta,
                client_text_hint=client_text_hint,
                client_text_source=client_text_source,
            )
            if request_id:
                edge_observability.log_asr_transcription(
                    request_id,
                    provider=self._fallback.provider_name,
                    source=fallback_result.source,
                    confidence=fallback_result.confidence,
                    latency_ms=int((time.perf_counter() - fallback_started_at) * 1000),
                    payload={
                        "audio_format": audio_meta.format,
                        "audio_duration_ms": audio_meta.duration_ms,
                        "audio_sample_rate_hz": audio_meta.sample_rate_hz,
                        "audio_channels": audio_meta.channels,
                        "client_asr_text": client_text_hint,
                        "client_asr_source": client_text_source,
                        "recognized_text": fallback_result.text,
                        "recognized_text_length": len(fallback_result.text),
                        "model_ref": model_ref,
                        "device": settings.local_asr_device,
                        "failed_provider": self._provider.provider_name,
                        "fallback_used": True,
                    },
                )
            return fallback_result


speech_recognition_service = SpeechRecognitionService()
