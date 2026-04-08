import base64
import inspect
import importlib
import sys
import traceback
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
                    "traceback": traceback.format_exc(),
                    "tts_mode": settings.tts_mode,
                    "tts_model": settings.tts_model,
                    "tts_repo_path": settings.tts_repo_path,
                    "tts_device": settings.tts_device,
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
        outputs = self._invoke_tts(model, text)

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

    def _invoke_tts(self, model, text: str):
        mode = settings.tts_mode
        if mode == "cosyvoice2_sft":
            return self._invoke_sft(model, text)
        if mode in {"cosyvoice_text", "cosyvoice_inference"}:
            return self._invoke_plain_text(model, text)
        if mode == "cosyvoice3_zero_shot":
            return self._invoke_zero_shot(model, text)
        if mode in {
            "cosyvoice3_instruct2",
            "cosyvoice_instruct2",
            "cosyvoice_instruct",
            "cosyvoice_300m_instruct",
        }:
            return self._invoke_instruct(model, text)

        raise RuntimeError(
            f"Unsupported TTS_MODE={mode!r}. "
            "Supported modes: 'cosyvoice2_sft', 'cosyvoice_text', "
            "'cosyvoice3_zero_shot', 'cosyvoice3_instruct2', "
            "'cosyvoice_instruct', 'cosyvoice_300m_instruct'."
        )

    def _invoke_sft(self, model, text: str):
        method = getattr(model, "inference_sft", None)
        if not callable(method):
            raise RuntimeError("TTS_MODE='cosyvoice2_sft' requires model.inference_sft, but it is unavailable.")

        speaker_id = self._resolve_speaker_id(model)
        if not speaker_id:
            raise RuntimeError(
                "TTS_MODE='cosyvoice2_sft' requires a preset speaker, "
                "but the loaded model exposes no available speaker_id."
            )

        return method(
            text,
            speaker_id,
            stream=False,
            speed=settings.tts_speed,
        )

    def _invoke_plain_text(self, model, text: str):
        errors: list[str] = []
        fallback_methods = ("inference", "inference_tts")
        fallback_kwargs = {
            "text": text,
            "tts_text": text,
            "stream": False,
            "speed": settings.tts_speed,
        }

        for method_name in fallback_methods:
            method = getattr(model, method_name, None)
            if not callable(method):
                continue
            try:
                signature = inspect.signature(method)
                allowed = {k: v for k, v in fallback_kwargs.items() if k in signature.parameters}
                return method(**allowed)
            except Exception as exc:
                errors.append(f"{method_name} failed: {type(exc).__name__}: {exc}")

        raise RuntimeError(
            "TTS_MODE='cosyvoice_text' could not find a usable plain-text inference path. "
            + " | ".join(errors)
        )

    def _invoke_zero_shot(self, model, text: str):
        method = getattr(model, "inference_zero_shot", None)
        if not callable(method):
            raise RuntimeError(
                "TTS_MODE='cosyvoice3_zero_shot' requires model.inference_zero_shot, but it is unavailable."
            )

        prompt_wav = settings.tts_prompt_wav_path
        if not prompt_wav:
            raise RuntimeError(
                "TTS_MODE='cosyvoice3_zero_shot' requires TTS_PROMPT_WAV "
                "or a repo asset/zero_shot_prompt.wav."
            )

        return method(
            tts_text=self._normalize_cosyvoice3_text(text),
            prompt_text=self._normalize_cosyvoice3_prompt(settings.tts_prompt_text),
            prompt_wav=prompt_wav,
            stream=False,
            speed=settings.tts_speed,
        )

    def _invoke_instruct(self, model, text: str):
        normalized_text = self._normalize_cosyvoice3_text(text)
        normalized_instruct = self._normalize_cosyvoice3_prompt(settings.tts_instruct_text)
        prompt_wav = settings.tts_prompt_wav_path
        speaker_id = settings.tts_speaker_id or self._resolve_speaker_id(model)

        candidates = []
        for method_name in ("inference_instruct2", "inference_instruct"):
            method = getattr(model, method_name, None)
            if not callable(method):
                continue
            candidates.append(
                (
                    method_name,
                    method,
                    [
                        {
                            "tts_text": normalized_text,
                            "text": normalized_text,
                            "instruct_text": normalized_instruct,
                            "spk_id": speaker_id,
                            "speaker_id": speaker_id,
                            "prompt_wav": prompt_wav,
                            "stream": False,
                            "speed": settings.tts_speed,
                        },
                        {
                            "tts_text": normalized_text,
                            "text": normalized_text,
                            "instruct_text": normalized_instruct,
                            "spk_id": speaker_id,
                            "speaker_id": speaker_id,
                            "stream": False,
                            "speed": settings.tts_speed,
                        },
                    ],
                )
            )

        if not candidates:
            raise RuntimeError(
                "Instruct TTS mode requires model.inference_instruct2 or model.inference_instruct, "
                "but neither method is available on the loaded CosyVoice model."
            )

        errors: list[str] = []
        for method_name, method, kwargs_candidates in candidates:
            try:
                return self._call_with_compatible_kwargs(method, kwargs_candidates)
            except Exception as exc:
                errors.append(f"{method_name} failed: {type(exc).__name__}: {exc}")

        raise RuntimeError(
            "Instruct TTS inference failed for all known CosyVoice entrypoints. "
            + " | ".join(errors)
        )

    def _call_with_compatible_kwargs(self, method, kwargs_candidates: list[dict]):
        signature = inspect.signature(method)
        parameters = signature.parameters
        accepts_var_kwargs = any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()
        )
        required = {
            name
            for name, parameter in parameters.items()
            if parameter.kind in {inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY}
            and parameter.default is inspect.Signature.empty
        }
        errors: list[str] = []

        for kwargs in kwargs_candidates:
            filtered_kwargs = kwargs if accepts_var_kwargs else {k: v for k, v in kwargs.items() if k in parameters}
            missing = sorted(name for name in required if name not in filtered_kwargs)
            if missing:
                errors.append(f"missing required parameters: {', '.join(missing)}")
                continue
            try:
                return method(**filtered_kwargs)
            except Exception as exc:
                errors.append(f"{type(exc).__name__}: {exc}")

        raise RuntimeError(" | ".join(errors) or "No compatible call signature matched the loaded model method.")

    def _resolve_speaker_id(self, model) -> str | None:
        spk2info = getattr(model, "spk2info", None)
        if not isinstance(spk2info, dict) or not spk2info:
            return None

        if settings.tts_speaker_id in spk2info:
            return settings.tts_speaker_id

        return next(iter(spk2info.keys()))

    def _normalize_cosyvoice3_prompt(self, text: str) -> str:
        cleaned = text.strip()
        if not cleaned:
            raise RuntimeError("CosyVoice3 prompt text is empty.")
        if "<|endofprompt|>" not in cleaned:
            cleaned = f"{cleaned}<|endofprompt|>"
        return cleaned

    def _normalize_cosyvoice3_text(self, text: str) -> str:
        cleaned = text.strip()
        if not cleaned:
            raise RuntimeError("CosyVoice3 tts_text is empty.")
        if "<|endofprompt|>" not in cleaned:
            cleaned = f"<|endofprompt|>{cleaned}"
        return cleaned

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
