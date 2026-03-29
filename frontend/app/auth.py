"""
Simple /api/auth/login and /api/auth/register endpoints for local dev.

In production these are handled by Supabase. Locally they create/verify
users in the PostgreSQL DB and return a signed JWT.
"""
from __future__ import annotations

import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db import get_session

try:
    from passlib.context import CryptContext
    _pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    def _hash(pw: str) -> str:   return _pwd_ctx.hash(pw)
    def _verify(pw: str, h: str) -> bool: return _pwd_ctx.verify(pw, h)
except Exception:
    import hashlib
    def _hash(pw: str) -> str:   return hashlib.sha256(pw.encode()).hexdigest()
    def _verify(pw: str, h: str) -> bool: return _hash(pw) == h

import base64 as _b64
import hashlib as _hl
import json as _json

_SECRET = os.getenv("SECRET_KEY", "dev-secret-change-me")

def _make_token(user_id: str, email: str) -> str:
    """3-part signed token: header.payload.sig — JWT-compatible structure."""
    import hmac as _hmac
    header = _b64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip("=")
    payload_json = _json.dumps({"sub": user_id, "email": email})
    payload = _b64.urlsafe_b64encode(payload_json.encode()).decode().rstrip("=")
    signing_input = f"{header}.{payload}".encode()
    sig = _hmac.new(_SECRET.encode(), signing_input, _hl.sha256).hexdigest()
    return f"{header}.{payload}.{sig}"

router = APIRouter()

ALLOW_DEV_AUTH = os.getenv("ALLOW_DEV_AUTH", "false").lower() == "true"


class AuthRequest(BaseModel):
    email: str
    password: str
    full_name: str | None = None


@router.post("/login")
async def login(body: AuthRequest, session: AsyncSession = Depends(get_session)):
    row = (await session.execute(
        text("SELECT id, password_hash, full_name FROM users WHERE email = :e LIMIT 1"),
        {"e": body.email},
    )).mappings().first()

    if row is None:
        # Dev mode: auto-create user on first login
        if ALLOW_DEV_AUTH:
            return await _create_and_return(body.email, body.password, body.email.split("@")[0], session)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Неправильний email або пароль")

    pw_hash = row.get("password_hash") or ""
    if pw_hash and not _verify(body.password, pw_hash):
        if not ALLOW_DEV_AUTH:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Неправильний email або пароль")
        # Dev mode: accept any password

    token = _make_token(str(row["id"]), body.email)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/register")
async def register(body: AuthRequest, session: AsyncSession = Depends(get_session)):
    exists = (await session.execute(
        text("SELECT 1 FROM users WHERE email = :e LIMIT 1"), {"e": body.email}
    )).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Користувач з таким email вже існує")
    return await _create_and_return(body.email, body.password, body.full_name, session)


async def _create_and_return(email: str, password: str, name: str | None, session: AsyncSession):
    user_id = str(uuid.uuid4())
    pw_hash = _hash(password) if password else ""
    await session.execute(
        text("""
            INSERT INTO users (id, email, full_name, role)
            VALUES (:id, :email, :name, 'user')
            ON CONFLICT (email) DO NOTHING
        """),
        {"id": user_id, "email": email, "name": name or email.split("@")[0]},
    )
    await session.commit()

    # Re-fetch id in case of conflict
    row = (await session.execute(
        text("SELECT id FROM users WHERE email = :e LIMIT 1"), {"e": email}
    )).mappings().first()
    real_id = str(row["id"]) if row else user_id

    token = _make_token(real_id, email)
    return {"access_token": token, "token_type": "bearer"}
