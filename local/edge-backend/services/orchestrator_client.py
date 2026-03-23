import httpx

from config import settings
from models import ChatResponse, RemoteChatRequest


class RemoteServiceError(Exception):
    def __init__(self, detail: str, status_code: int = 502) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class OrchestratorClient:
    def __init__(self) -> None:
        self._base_url = settings.cloud_api_base
        self._timeout = settings.request_timeout_seconds

    async def send_chat(self, request: RemoteChatRequest) -> ChatResponse:
        url = f"{self._base_url}/chat"
        request_payload = request.model_dump() if hasattr(request, "model_dump") else request.dict()

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=request_payload)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise RemoteServiceError(
                detail="Remote orchestrator timed out.",
                status_code=504,
            ) from exc
        except httpx.HTTPStatusError as exc:
            detail = _parse_remote_error(exc.response)
            raise RemoteServiceError(detail=detail, status_code=exc.response.status_code) from exc
        except httpx.RequestError as exc:
            raise RemoteServiceError(
                detail="Remote orchestrator is unreachable.",
                status_code=502,
            ) from exc

        response_payload = response.json()
        if hasattr(ChatResponse, "model_validate"):
            return ChatResponse.model_validate(response_payload)
        return ChatResponse(**response_payload)


def _parse_remote_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return "Remote orchestrator returned a non-JSON error."

    detail = payload.get("detail")
    if isinstance(detail, str) and detail:
        return detail

    return "Remote orchestrator returned an unexpected error."


orchestrator_client = OrchestratorClient()
