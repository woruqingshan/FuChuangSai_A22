from fastapi import APIRouter, Request, Response

from config import settings
from models import SessionBootstrapResponse
from services.session_service import BEIJING_TZ, session_service

router = APIRouter()


@router.post("/session", response_model=SessionBootstrapResponse)
async def bootstrap_session(request: Request, response: Response) -> SessionBootstrapResponse:
    cookie_token = request.cookies.get(settings.session_cookie_name)
    record, next_cookie_token, cookie_created = session_service.bootstrap_session(cookie_token)

    if cookie_created:
        response.set_cookie(
            key=settings.session_cookie_name,
            value=next_cookie_token,
            path="/",
            httponly=True,
            secure=settings.session_cookie_secure,
            samesite=settings.session_cookie_samesite,
        )

    return SessionBootstrapResponse(
        status="ready",
        session_id=record.session_id,
        stream_id=record.stream_id,
        created_at=record.created_at.astimezone(BEIJING_TZ).isoformat(),
        next_turn_id=record.next_turn_id,
    )
