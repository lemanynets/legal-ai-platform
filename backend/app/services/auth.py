"""
Token validation service — HMAC-SHA256 signed tokens.

Token format: base64url(json_payload).hmac_hex
where json_payload = {"sub": user_id, "email": email}
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db import get_session

_bearer = HTTPBearer(auto_error=False)
_SECRET = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALLOW_DEV_AUTH = os.getenv("ALLOW_DEV_AUTH", "false").lower() == "true"
_DEV_EMAIL = "dev@legal-ai.local"


def _decode_token(token: str) -> dict | None:
    try:
        parts = token.split(".")
        if len(parts) == 3:
            header, payload_b64, sig = parts
            signing_input = f"{header}.{payload_b64}".encode()
            expected = hmac.new(_SECRET.encode(), signing_input, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected):
                return None
            payload_bytes = base64.urlsafe_b64decode(payload_b64 + "==")
            return json.loads(payload_bytes)
        if len(parts) == 2:
            payload_b64, sig = parts
            payload_bytes = base64.urlsafe_b64decode(payload_b64.encode() + b"==")
            expected = hmac.new(_SECRET.encode(), payload_bytes, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected):
                return None
            return json.loads(payload_bytes)
    except Exception:
        return None
    return None


async def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
):
    """Return the authenticated user row dict or raise 401."""

    if ALLOW_DEV_AUTH and (creds is None or creds.credentials in ("dev-token", "")):
        return await _get_or_create_dev_user(session)

    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    data = _decode_token(creds.credentials)
    if not data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    row = (
        await session.execute(
            text("SELECT id, email, full_name, company, role FROM users WHERE id = :id LIMIT 1"),
            {"id": data["sub"]},
        )
    ).mappings().first()

    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return dict(row)


async def _get_or_create_dev_user(session: AsyncSession) -> dict:
    import uuid
    _DEV_USER_ID = "00000000-0000-0000-0000-000000000001"

    row = (
        await session.execute(
            text("SELECT id, email, full_name, company, role FROM users WHERE email = :e LIMIT 1"),
            {"e": _DEV_EMAIL},
        )
    ).mappings().first()
    if row:
        return dict(row)

    await session.execute(
        text("""
            INSERT INTO users (id, email, full_name, role)
            VALUES (:id, :email, 'Dev User', 'admin')
            ON CONFLICT (email) DO NOTHING
        """),
        {"id": _DEV_USER_ID, "email": _DEV_EMAIL},
    )
    await session.commit()
    return {"id": _DEV_USER_ID, "email": _DEV_EMAIL, "full_name": "Dev User", "role": "admin"}
