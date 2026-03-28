import json

from config import settings
from models import ExtractRequest, ExtractResponse, VisionFeatures
from services.qwen_vl_runtime import qwen_vl_runtime
from services.storage import vision_storage


class FrameFeatureExtractor:
    def extract(self, request: ExtractRequest) -> ExtractResponse:
        processed_frame_count = len(request.video_frames)
        video_meta = request.video_meta

        if not processed_frame_count and not video_meta:
            return ExtractResponse(
                vision_features=None,
                video_meta=video_meta,
                processed_frame_count=0,
                extractor_mode=settings.extractor_mode,
            )

        motion_level = "still"
        if processed_frame_count >= 5:
            motion_level = "moderate"
        elif processed_frame_count >= 3:
            motion_level = "low"

        summary_parts = []
        if processed_frame_count:
            summary_parts.append(f"{processed_frame_count} key frames captured")
        if video_meta and video_meta.width and video_meta.height:
            summary_parts.append(f"{video_meta.width}x{video_meta.height}")

        if settings.extractor_mode == "qwen2_5_vl":
            vision_features = qwen_vl_runtime.extract(request)
        else:
            vision_features = VisionFeatures(
                scene_summary=", ".join(summary_parts) or "video turn captured",
                attention_target="camera",
                motion_level=motion_level,
                emotion_tags=[],
                source="remote_vision_service",
                frame_count=processed_frame_count or (video_meta.sampled_frame_count if video_meta else 0),
            )

        if video_meta:
            serialized_video_meta = video_meta.model_dump() if hasattr(video_meta, "model_dump") else video_meta.dict()
            vision_storage.persist_payload(
                session_id=request.session_id,
                turn_id=request.turn_id,
                file_name="video_meta.json",
                payload=json.loads(json.dumps(serialized_video_meta, ensure_ascii=False, default=str)),
            )
        serialized_vision_features = (
            vision_features.model_dump() if hasattr(vision_features, "model_dump") else vision_features.dict()
        )
        vision_storage.persist_payload(
            session_id=request.session_id,
            turn_id=request.turn_id,
            file_name="vision_features.json",
            payload=json.loads(json.dumps(serialized_vision_features, ensure_ascii=False, default=str)),
        )

        return ExtractResponse(
            vision_features=vision_features,
            video_meta=video_meta,
            processed_frame_count=processed_frame_count,
            extractor_mode=settings.extractor_mode,
        )


frame_feature_extractor = FrameFeatureExtractor()
