import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from config import settings

router = APIRouter()

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}

FORWARDED_REQUEST_HEADERS = {
    "range",
    "if-range",
}

FORWARDED_RESPONSE_HEADERS = {
    "accept-ranges",
    "cache-control",
    "content-disposition",
    "content-length",
    "content-range",
    "etag",
    "expires",
    "last-modified",
    "pragma",
}


@router.get("/media/video-stream/{session_id}/{turn_id}/manifest")
async def proxy_video_manifest(session_id: str, turn_id: int) -> Response:
    upstream_path = f"/media/video-stream/{session_id}/{turn_id}/manifest"
    timeout = httpx.Timeout(settings.media_connect_timeout_seconds, read=settings.media_manifest_timeout_seconds)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            upstream = await client.get(f"{settings.cloud_api_base}{upstream_path}")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Remote media manifest is unreachable.") from exc

    headers = _filter_response_headers(upstream.headers)
    headers["cache-control"] = "no-store, no-cache, must-revalidate, max-age=0"
    headers["pragma"] = "no-cache"
    headers["expires"] = "0"
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "application/json"),
        headers=headers,
    )


@router.api_route("/media/video-chunk/{session_id}/{turn_id}/{chunk_index}", methods=["GET", "HEAD"])
async def proxy_video_chunk(request: Request, session_id: str, turn_id: int, chunk_index: int) -> Response:
    upstream_path = f"/media/video-chunk/{session_id}/{turn_id}/{chunk_index}"
    return await _stream_remote_media(request, upstream_path)


@router.api_route("/media/video/{session_id}/{turn_id}", methods=["GET", "HEAD"])
async def proxy_video(request: Request, session_id: str, turn_id: int) -> Response:
    upstream_path = f"/media/video/{session_id}/{turn_id}"
    return await _stream_remote_media(request, upstream_path)


async def _stream_remote_media(request: Request, upstream_path: str) -> Response:
    timeout = httpx.Timeout(
        settings.media_connect_timeout_seconds,
        read=settings.media_read_timeout_seconds,
        write=settings.media_connect_timeout_seconds,
        pool=settings.media_connect_timeout_seconds,
    )
    client = httpx.AsyncClient(timeout=timeout)
    upstream_request = client.build_request(
        request.method,
        f"{settings.cloud_api_base}{upstream_path}",
        headers=_filter_request_headers(request.headers),
    )
    try:
        upstream = await client.send(upstream_request, stream=True)
    except httpx.HTTPError as exc:
        await client.aclose()
        raise HTTPException(status_code=502, detail="Remote media is unreachable.") from exc

    headers = _filter_response_headers(upstream.headers)
    media_type = upstream.headers.get("content-type", "video/mp4")

    if request.method == "HEAD":
        await upstream.aclose()
        await client.aclose()
        return Response(status_code=upstream.status_code, headers=headers, media_type=media_type)

    return StreamingResponse(
        upstream.aiter_bytes(),
        status_code=upstream.status_code,
        media_type=media_type,
        headers=headers,
        background=BackgroundTask(_close_stream, upstream, client),
    )


async def _close_stream(upstream: httpx.Response, client: httpx.AsyncClient) -> None:
    await upstream.aclose()
    await client.aclose()


def _filter_request_headers(headers) -> dict[str, str]:
    return {
        key: value
        for key, value in headers.items()
        if key.lower() in FORWARDED_REQUEST_HEADERS
    }


def _filter_response_headers(headers) -> dict[str, str]:
    return {
        key: value
        for key, value in headers.items()
        if key.lower() in FORWARDED_RESPONSE_HEADERS and key.lower() not in HOP_BY_HOP_HEADERS
    }
