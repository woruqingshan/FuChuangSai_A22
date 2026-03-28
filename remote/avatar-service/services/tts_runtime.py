import base64
import importlib
import sys
import wave
from io import BytesIO
from pathlib import Path

import numpy as np
import torch

from config import settings
from services.storage import avatar_storage


class TTSRuntime:
    def __init__(self) -> None:
        self._model = None

    def warmup(self) -> None:
        if not settings.tts_warmup_enabled:
            return
        try:
            self._ensure_model()
        except Exception:
            # Keep avatar-service available even before the CosyVoice runtime is fully ready.
            pass

    def synthesize(self, *, session_id: str, turn_id: int, text: str) -> str | None:
        if not text.strip():
            return None
        if settings.tts_mode == "placeholder":
            return None

        try:
            model = self._ensure_model()
            waveform, sample_rate = self._run_inference(model, text)
            audio_bytes = self._to_wav_bytes(waveform, sample_rate)
            avatar_storage.persist_audio(session_id=session_id, turn_id=turn_id, audio_bytes=audio_bytes)
            encoded = base64.b64encode(audio_bytes).decode("ascii")
            return f"data:audio/wav;base64,{encoded}"
        except Exception as exc:
            avatar_storage.persist_runtime_error(
                session_id=session_id,
                turn_id=turn_id,
                payload={
                    "error_type": type(exc).__name__,
                    "detail": str(exc),
                },
            )
            return None

    def _ensure_model(self):
        if self._model is not None:
            return self._model

        AutoModel = self._resolve_auto_model()
        self._model = AutoModel(model_dir=settings.tts_model)
        return self._model

    def _resolve_auto_model(self):
        try:
            module = importlib.import_module("cosyvoice.cli.cosyvoice")
            return getattr(module, "AutoModel")
        except Exception:
            self._extend_sys_path_from_repo()
            module = importlib.import_module("cosyvoice.cli.cosyvoice")
            return getattr(module, "AutoModel")

    def _extend_sys_path_from_repo(self) -> None:
        if not settings.tts_repo_path:
            return

        repo_path = Path(settings.tts_repo_path).expanduser()
        matcha_path = repo_path / "third_party" / "Matcha-TTS"
        for candidate in (repo_path, matcha_path):
            if candidate.exists() and str(candidate) not in sys.path:
                sys.path.append(str(candidate))

    def _run_inference(self, model, text: str) -> tuple[np.ndarray, int]:
        sample_rate = int(getattr(model, "sample_rate", 22050))
        outputs = model.inference_sft(
            text,
            settings.tts_speaker_id,
            stream=False,
            speed=settings.tts_speed,
        )

        chunks: list[np.ndarray] = []
        for item in outputs:
            speech = item.get("tts_speech")
            if speech is None:
                continue
            if isinstance(speech, torch.Tensor):
                chunk = speech.squeeze().detach().cpu().float().numpy()
            else:
                chunk = np.asarray(speech, dtype=np.float32).squeeze()
            if chunk.size:
                chunks.append(chunk)

        if not chunks:
            raise RuntimeError("CosyVoice returned no audio frames.")

        return np.concatenate(chunks, axis=0), sample_rate

    def _to_wav_bytes(self, waveform: np.ndarray, sample_rate: int) -> bytes:
        normalized = np.clip(waveform, -1.0, 1.0)
        pcm16 = (normalized * 32767.0).astype(np.int16)

        buffer = BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm16.tobytes())
        return buffer.getvalue()


tts_runtime = TTSRuntime()
