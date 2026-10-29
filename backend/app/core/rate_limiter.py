from fastapi import Request
from slowapi import Limiter


def client_address(request: Request) -> str:
    """
    The caller's real address. Render sits behind Cloudflare, so request.client is Render's proxy and
    would put every user in one bucket. CF-Connecting-IP is set (and overwritten) by Cloudflare;
    X-Forwarded-For is never used because a client can type anything into it.
    """
    cf = request.headers.get("cf-connecting-ip", "").strip()
    if cf:
        return cf[:64]
    return request.client.host if request.client else "unknown"


limiter = Limiter(
    key_func=client_address,
)
