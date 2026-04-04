from __future__ import annotations

from dataclasses import dataclass

import httpx
from fastapi import Header, HTTPException

from app.config import settings


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    email: str


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        return ""
    prefix = "bearer "
    raw = authorization.strip()
    if raw.lower().startswith(prefix):
        return raw[len(prefix) :].strip()
    return ""


def _allowed_dev_demo_users() -> set[str]:
    return {item.strip() for item in settings.allowed_dev_demo_users.split(",") if item.strip()}


def _normalize_demo_user(value: str | None) -> str:
    demo_user = (value or "").strip() or "demo-user"
    allowed = _allowed_dev_demo_users()
    # Allow any user when list is empty; otherwise check against allowlist
    if allowed and demo_user not in allowed:
        # Also accept if the base name (strip "dev-" prefix) is in the list
        base = demo_user.removeprefix("dev-")
        if base not in allowed:
            raise HTTPException(status_code=403, detail="Unknown demo user")
    return demo_user


def _supabase_user_from_token(token: str) -> CurrentUser:
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(
            status_code=401,
            detail="Supabase auth is not configured on server side.",
        )

    auth_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/user"
    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": settings.supabase_anon_key,
    }
    try:
        response = httpx.get(auth_url, headers=headers, timeout=10.0)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Auth service unavailable: {exc}") from exc

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired access token.")

    data = response.json()
    user_id = str(data.get("id") or "").strip()
    email = str(data.get("email") or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Supabase response missing user id.")
    return CurrentUser(user_id=user_id, email=email)


def _ensure_dev_auth_allowed() -> None:
    allowed_envs = {"local", "dev", "development", "test"}
    if settings.app_env not in allowed_envs:
        raise HTTPException(status_code=403, detail="Dev auth disabled outside local environments")


def get_current_user(
    authorization: str | None = Header(default=None),
    x_demo_user: str | None = Header(default=None),
) -> CurrentUser:
    token = _extract_bearer_token(authorization)
    if token:
        if settings.allow_dev_auth and token.startswith("dev-token-"):
            _ensure_dev_auth_allowed()
            demo_user = _normalize_demo_user(token.replace("dev-token-", "", 1))
            return CurrentUser(user_id=demo_user, email=f"{demo_user}@local.dev")

        # Try custom JWT first
        from app.services.security import verify_access_token

        payload = verify_access_token(token)
        if payload and "sub" in payload:
            return CurrentUser(user_id=payload["sub"], email=payload.get("email", ""))

        # Fallback to Supabase
        return _supabase_user_from_token(token)

    if settings.allow_dev_auth:
        _ensure_dev_auth_allowed()
        demo_user = _normalize_demo_user(x_demo_user)
        return CurrentUser(user_id=demo_user, email=f"{demo_user}@local.dev")

    raise HTTPException(status_code=401, detail="Authorization header required.")
