from collections.abc import AsyncIterator

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
    upstream_method = "GET" if request.method == "HEAD" else request.method
    client = httpx.AsyncClient(timeout=timeout)
    upstream_request = client.build_request(
        upstream_method,
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
    range_header = request.headers.get("range")
    range_spec = _parse_byte_range(range_header, upstream.headers.get("content-length"))

    if request.method == "HEAD":
        if upstream.status_code == 200 and range_spec:
            start, end, total = range_spec
            headers.update(_range_headers(start, end, total))
            status_code = 206
        else:
            status_code = upstream.status_code
        await upstream.aclose()
        await client.aclose()
        return Response(status_code=status_code, headers=headers, media_type=media_type)

    if upstream.status_code == 200 and range_spec:
        start, end, total = range_spec
        headers.update(_range_headers(start, end, total))
        return StreamingResponse(
            _iter_byte_range(upstream, client, start, end - start + 1),
            status_code=206,
            media_type=media_type,
            headers=headers,
        )

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


async def _iter_byte_range(
    upstream: httpx.Response,
    client: httpx.AsyncClient,
    start: int,
    length: int,
) -> AsyncIterator[bytes]:
    skip_remaining = start
    send_remaining = length
    try:
        async for chunk in upstream.aiter_bytes():
            if skip_remaining:
                if len(chunk) <= skip_remaining:
                    skip_remaining -= len(chunk)
                    continue
                chunk = chunk[skip_remaining:]
                skip_remaining = 0

            if send_remaining <= 0:
                break

            if len(chunk) > send_remaining:
                yield chunk[:send_remaining]
                break

            yield chunk
            send_remaining -= len(chunk)
    finally:
        await upstream.aclose()
        await client.aclose()


def _parse_byte_range(range_header: str | None, content_length: str | None) -> tuple[int, int, int] | None:
    if not range_header or not content_length:
        return None
    if not range_header.startswith("bytes="):
        return None
    try:
        total = int(content_length)
    except ValueError:
        return None
    if total <= 0 or "," in range_header:
        return None

    start_text, _, end_text = range_header.removeprefix("bytes=").partition("-")
    try:
        if start_text:
            start = int(start_text)
            end = int(end_text) if end_text else total - 1
        elif end_text:
            suffix_length = int(end_text)
            if suffix_length <= 0:
                return None
            start = max(total - suffix_length, 0)
            end = total - 1
        else:
            return None
    except ValueError:
        return None

    if start < 0 or start >= total:
        return None
    end = min(end, total - 1)
    if end < start:
        return None
    return start, end, total


def _range_headers(start: int, end: int, total: int) -> dict[str, str]:
    return {
        "accept-ranges": "bytes",
        "content-length": str(end - start + 1),
        "content-range": f"bytes {start}-{end}/{total}",
    }


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
