from fastapi import APIRouter, HTTPException, Request

from config import settings
from models import JobStatusResponse
from services.access_service import AccessError, access_service
from services.job_manager import job_manager
from services.session_service import SessionError, session_service

router = APIRouter()


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(request: Request, job_id: str) -> JobStatusResponse:
    try:
        session = session_service.require_session(request.cookies.get(settings.session_cookie_name))
        access_service.require_access(
            session=session,
            access_token=request.cookies.get(settings.access_cookie_name),
        )
    except SessionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except AccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    job = await job_manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.session_id != session.session_id:
        raise HTTPException(status_code=403, detail="Job does not belong to the current session.")

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        queue_position=await job_manager.queue_position(job.job_id),
        chat_response_ready=job.chat_response is not None,
        chat_response=job.chat_response,
        error=job.error,
    )
