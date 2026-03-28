"""
JWT-based authentication service.

Validates Bearer tokens issued by Supabase (or dev tokens in ALLOW_DEV_AUTH mode).
"""
from __future__ import annotations

import os
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db import get_session
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)

ALLOW_DEV_AUTH = os.getenv("ALLOW_DEV_AUTH", "false").lower() == "true"
_DEV_USER_ID = "00000000-0000-0000-0000-000000000001"
_DEV_EMAIL = "dev@legal-ai.local"


async def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Return the authenticated User object or raise 401."""

    # ── Dev mode bypass ───────────────────────────────────────────────────────
    if ALLOW_DEV_AUTH and (creds is None or creds.credentials == "dev-token"):
        user = await _get_or_create_dev_user(session)
        return user

    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    # ── Production: validate Supabase JWT ─────────────────────────────────────
    # In a real deployment this would decode the JWT and verify with Supabase keys.
    # For Docker local testing we accept any non-empty token and look up the user.
    token = creds.credentials
    try:
        import jose.jwt as jwt_lib  # type: ignore
        supabase_secret = os.getenv("SUPABASE_JWT_SECRET", "")
        if supabase_secret:
            payload = jwt_lib.decode(token, supabase_secret, algorithms=["HS256"])
            user_id = payload.get("sub")
        else:
            # No secret configured — fall back to dev user in Docker env
            user_id = _DEV_USER_ID
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    row = (
        await session.execute(
            text("SELECT id, email, full_name, company, role FROM users WHERE id = :uid LIMIT 1"),
            {"uid": user_id},
        )
    ).mappings().first()

    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Build a lightweight User ORM object from the raw row
    u = User()
    u.id = row["id"]
    u.email = row["email"]
    u.full_name = row.get("full_name")
    u.company = row.get("company")
    u.role = row.get("role", "user")
    return u


async def _get_or_create_dev_user(session: AsyncSession) -> User:
    """Return (or create) the dev@legal-ai.local user for local testing."""
    row = (
        await session.execute(
            text("SELECT id, email, full_name, company, role FROM users WHERE email = :email LIMIT 1"),
            {"email": _DEV_EMAIL},
        )
    ).mappings().first()

    if row:
        u = User()
        u.id = row["id"]
        u.email = row["email"]
        u.full_name = row.get("full_name")
        u.company = row.get("company")
        u.role = row.get("role", "user")
        return u

    # Create dev user
    await session.execute(
        text("""
            INSERT INTO users (id, email, full_name, role)
            VALUES (:id, :email, :name, 'admin')
            ON CONFLICT (email) DO NOTHING
        """),
        {"id": _DEV_USER_ID, "email": _DEV_EMAIL, "name": "Dev User"},
    )
    await session.commit()

    u = User()
    u.id = _DEV_USER_ID  # type: ignore[assignment]
    u.email = _DEV_EMAIL
    u.full_name = "Dev User"
    u.role = "admin"
    return u
