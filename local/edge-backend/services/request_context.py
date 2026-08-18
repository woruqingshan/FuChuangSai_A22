from fastapi import Request


TRUSTED_CLIENT_IP_HEADER = "x-a22-client-ip"


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get(TRUSTED_CLIENT_IP_HEADER)
    if forwarded:
        return forwarded.strip()
    return request.client.host if request.client else "unknown"
