from fastapi import APIRouter, HTTPException, Request, Response

from config import settings
from models import AccessStatusResponse, AccessVerifyRequest, AccessVerifyResponse
from services.access_service import AccessError, access_service
from services.rate_limiter import rate_limiter
from services.request_context import get_client_ip
from services.session_service import SessionError, session_service

router = APIRouter()


@router.get("/access/status", response_model=AccessStatusResponse)
async def access_status(request: Request) -> AccessStatusResponse:
    try:
        session = session_service.require_session(request.cookies.get(settings.session_cookie_name))
    except SessionError:
        return AccessStatusResponse(authorized=False)
    authorized = access_service.is_authorized(
        session=session,
        access_token=request.cookies.get(settings.access_cookie_name),
    )
    return AccessStatusResponse(authorized=authorized)


@router.post("/access/verify", response_model=AccessVerifyResponse)
async def verify_access(
    request: Request,
    response: Response,
    payload: AccessVerifyRequest,
) -> AccessVerifyResponse:
    client_ip = get_client_ip(request)
    rate_result = rate_limiter.allow(
        f"access-verify:ip:{client_ip}",
        limit=settings.invitation_verify_rate_limit_count,
        window_seconds=settings.invitation_verify_rate_limit_window_seconds,
    )
    if not rate_result.allowed:
        raise HTTPException(
            status_code=429,
            detail={"reason": "rate_limited", "message": "Too many invitation attempts."},
            headers={"Retry-After": str(rate_result.retry_after_seconds)},
        )

    try:
        session = session_service.require_session(request.cookies.get(settings.session_cookie_name))
    except SessionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    try:
        _grant, access_token, token_created = access_service.verify_code(
            session=session,
            access_token=request.cookies.get(settings.access_cookie_name),
            code=payload.code,
        )
    except AccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    if token_created:
        response.set_cookie(
            key=settings.access_cookie_name,
            value=access_token,
            path="/",
            httponly=True,
            secure=settings.session_cookie_secure,
            samesite=settings.session_cookie_samesite,
        )

    return AccessVerifyResponse(authorized=True)
