from __future__ import annotations

from typing import Iterable

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.models import User
from app.services.subscriptions import get_or_create_user


ROLE_ALIASES: dict[str, str] = {
    "user": "owner",
    "owner": "owner",
    "admin": "admin",
    "lawyer": "lawyer",
    "analyst": "analyst",
    "viewer": "viewer",
}


def normalize_role(value: str | None) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return "owner"
    return ROLE_ALIASES.get(raw, raw)


def get_user_profile(db: Session, current_user: CurrentUser) -> User:
    return get_or_create_user(db, current_user)


def ensure_user_role(
    db: Session,
    *,
    current_user: CurrentUser,
    allowed_roles: Iterable[str],
    reason: str | None = None,
) -> User:
    user = get_user_profile(db, current_user)
    current_role = normalize_role(user.role)
    allowed = {normalize_role(item) for item in allowed_roles if str(item).strip()}
    if "*" in allowed:
        return user
    if current_role not in allowed:
        expected = ", ".join(sorted(allowed)) or "unknown"
        suffix = f" for {reason}" if reason else ""
        raise HTTPException(
            status_code=403,
            detail=f"Role '{current_role}' is not allowed{suffix}. Allowed roles: {expected}.",
        )
    return user
