from fastapi import Request

from app.auth import _allowed_dev_demo_users
from app.config import settings
from app.services.security import verify_access_token
from slowapi.util import get_remote_address


def _normalize_demo_user_for_rate_limit(raw: str | None) -> str | None:
    demo_user = (raw or "").strip() or "demo-user"
    allowed = _allowed_dev_demo_users()
    if allowed and demo_user not in allowed:
        return None
    return demo_user


def get_user_or_ip_key(request: Request) -> str:
    # Prefer a stable user id when possible, fall back to IP.
    auth_header = str(request.headers.get("authorization") or "").strip()
    token = ""
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()

    if token:
        if settings.allow_dev_auth and token.startswith("dev-token-"):
            demo_user = _normalize_demo_user_for_rate_limit(token.replace("dev-token-", "", 1))
            if demo_user:
                return f"dev:{demo_user}"
        payload = verify_access_token(token)
        if payload and payload.get("sub"):
            return f"user:{payload['sub']}"

    if settings.allow_dev_auth:
        demo_user = _normalize_demo_user_for_rate_limit(request.headers.get("x-demo-user"))
        if demo_user:
            return f"demo:{demo_user}"

    return get_remote_address(request)