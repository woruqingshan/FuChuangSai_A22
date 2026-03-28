from services.audio.contracts import AudioMeta, ProcessedAudioTurn, SpeechFeatures
from services.audio.feature_extractor import audio_feature_extractor
from services.audio.transcription_service import speech_recognition_service
from services.audio.wav_utils import decode_audio_base64, decode_wav_audio


class AudioTurnService:
    def process(
        self,
        *,
        audio_base64: str,
        audio_format: str | None,
        audio_duration_ms: int | None,
        audio_sample_rate_hz: int | None,
        audio_channels: int | None,
        client_asr_text: str | None,
        client_asr_source: str | None,
        request_id: str | None = None,
    ) -> ProcessedAudioTurn:
        audio_bytes = decode_audio_base64(audio_base64)
        normalized_format = (audio_format or "wav").strip().lower() or "wav"

        decoded_audio = None
        if normalized_format == "wav":
            try:
                decoded_audio = decode_wav_audio(audio_bytes)
            except ValueError:
                decoded_audio = None

        base_audio_meta = AudioMeta(
            format=normalized_format,
            duration_ms=audio_duration_ms,
            sample_rate_hz=audio_sample_rate_hz,
            channels=audio_channels,
            source="browser_microphone",
        )

        transcription_result = speech_recognition_service.transcribe(
            audio_bytes=audio_bytes,
            audio_meta=base_audio_meta,
            client_text_hint=client_asr_text,
            client_text_source=client_asr_source,
            request_id=request_id,
        )

        if decoded_audio is not None:
            audio_meta, speech_features = audio_feature_extractor.extract(
                decoded_audio,
                audio_format=normalized_format,
                transcript=transcription_result.text,
                transcript_confidence=transcription_result.confidence,
            )
            audio_meta.source = "browser_microphone"
        else:
            audio_meta = base_audio_meta
            speech_features = SpeechFeatures(
                transcript_confidence=transcription_result.confidence,
                emotion_tags=["steady"],
                source="metadata_only_audio_features",
            )

        if audio_meta.duration_ms is None:
            audio_meta.duration_ms = audio_duration_ms
        if audio_meta.sample_rate_hz is None:
            audio_meta.sample_rate_hz = audio_sample_rate_hz
        if audio_meta.channels is None:
            audio_meta.channels = audio_channels

        return ProcessedAudioTurn(
            user_text=transcription_result.text.strip() or "Audio input received from the local microphone.",
            text_source=transcription_result.source,
            alignment_mode="audio_only",
            audio_meta=audio_meta,
            speech_features=speech_features,
        )


audio_turn_service = AudioTurnService()
