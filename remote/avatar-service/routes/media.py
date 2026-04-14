from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from services.storage import avatar_storage

router = APIRouter()


@router.get("/media/video/{session_id}/{turn_id}")
async def get_turn_video(session_id: str, turn_id: int) -> FileResponse:
    video_path = avatar_storage.get_video_path(session_id=session_id, turn_id=turn_id)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Reply video not found.")

    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=f"{session_id}-{turn_id}.mp4",
        headers={
            "cache-control": "no-store, no-cache, must-revalidate, max-age=0",
            "pragma": "no-cache",
            "expires": "0",
        },
    )
