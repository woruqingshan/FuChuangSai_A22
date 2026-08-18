from fastapi import APIRouter, HTTPException, Request, Response

from config import settings
from models import AuthCredentialRequest, AuthMeResponse, AuthResponse, AuthUserPublic
from services.access_service import AccessError, access_service
from services.auth_service import AuthError, auth_service
from services.rate_limiter import rate_limiter
from services.request_context import get_client_ip
from services.session_service import SessionError, session_service


router = APIRouter()


@router.post("/auth/register", response_model=AuthResponse)
async def register(request: Request, response: Response, payload: AuthCredentialRequest) -> AuthResponse:
    _limit_auth_endpoint(
        request,
        scope="auth-register",
        limit=settings.register_ip_rate_limit_count,
        window_seconds=settings.register_ip_rate_limit_window_seconds,
    )
    try:
        session = session_service.require_session(request.cookies.get(settings.session_cookie_name))
        access_service.require_access(
            session=session,
            access_token=request.cookies.get(settings.access_cookie_name),
        )
        auth_session, auth_token = auth_service.register(username=payload.username, password=payload.password)
        session_service.bind_user(request.cookies.get(settings.session_cookie_name), auth_session.user_id)
    except SessionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except AccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail="请先完成体验邀请码验证。") from exc
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    _set_auth_cookie(response, auth_token)
    return AuthResponse(
        authenticated=True,
        user=AuthUserPublic(user_id=auth_session.user_id, username=auth_session.username),
    )


@router.post("/auth/login", response_model=AuthResponse)
async def login(request: Request, response: Response, payload: AuthCredentialRequest) -> AuthResponse:
    _limit_auth_endpoint(
        request,
        scope="auth-login",
        limit=settings.login_ip_rate_limit_count,
        window_seconds=settings.login_ip_rate_limit_window_seconds,
    )
    try:
        session_service.require_session(request.cookies.get(settings.session_cookie_name))
        auth_session, auth_token = auth_service.login(username=payload.username, password=payload.password)
        session_service.bind_user(request.cookies.get(settings.session_cookie_name), auth_session.user_id)
    except SessionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except AuthError as exc:
        public_detail = "用户名或密码错误" if exc.status_code == 401 else exc.detail
        raise HTTPException(status_code=exc.status_code, detail=public_detail) from exc

    _set_auth_cookie(response, auth_token)
    return AuthResponse(
        authenticated=True,
        user=AuthUserPublic(user_id=auth_session.user_id, username=auth_session.username),
    )


@router.post("/auth/logout", response_model=AuthMeResponse)
async def logout(request: Request, response: Response) -> AuthMeResponse:
    auth_service.logout(request.cookies.get(settings.auth_cookie_name))
    session_service.clear_user(request.cookies.get(settings.session_cookie_name))
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )
    return AuthMeResponse(authenticated=False)


@router.get("/auth/me", response_model=AuthMeResponse)
async def me(request: Request) -> AuthMeResponse:
    auth_session = auth_service.resolve(request.cookies.get(settings.auth_cookie_name))
    if not auth_session:
        return AuthMeResponse(authenticated=False)
    return AuthMeResponse(
        authenticated=True,
        user=AuthUserPublic(user_id=auth_session.user_id, username=auth_session.username),
    )


def _set_auth_cookie(response: Response, auth_token: str) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=auth_token,
        path="/",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        max_age=settings.auth_ttl_seconds,
    )


def _limit_auth_endpoint(request: Request, *, scope: str, limit: int, window_seconds: int) -> None:
    client_ip = get_client_ip(request)
    rate_result = rate_limiter.allow(
        f"{scope}:ip:{client_ip}",
        limit=limit,
        window_seconds=window_seconds,
    )
    if not rate_result.allowed:
        raise HTTPException(
            status_code=429,
            detail={"reason": "rate_limited", "message": "Too many account requests."},
            headers={"Retry-After": str(rate_result.retry_after_seconds)},
        )
