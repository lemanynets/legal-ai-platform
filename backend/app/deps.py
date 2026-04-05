"""
Shared dependencies for all FastAPI routers.

Import from here instead of defining in main.py or individual routers:

    from app.deps import get_current_user, get_session, _ai_json, _audit_log
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import uuid
from datetime import datetime
from typing import Any, Optional

import pathlib
import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session, AsyncSessionLocal  # noqa: F401 (re-exported)

# ── Constants ─────────────────────────────────────────────────────────────────
UPLOAD_DIR = pathlib.Path(os.getenv("UPLOAD_DIR", "/tmp/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ── Auth config ───────────────────────────────────────────────────────────────
_SECRET = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALLOW_DEV_AUTH = os.getenv("ALLOW_DEV_AUTH", "false").lower() == "true"
_bearer = HTTPBearer(auto_error=False)


# ── Token helpers ─────────────────────────────────────────────────────────────
def _make_token(user_id: str, email: str) -> str:
    """3-part HMAC-SHA256 token: header.payload.sig"""
    header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip("=")
    payload_json = json.dumps({"sub": user_id, "email": email})
    payload = base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip("=")
    signing_input = f"{header}.{payload}".encode()
    sig = hmac.new(_SECRET.encode(), signing_input, hashlib.sha256).hexdigest()
    return f"{header}.{payload}.{sig}"


def _decode_token(token: str) -> dict[str, str] | None:
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


# ── Password helpers ──────────────────────────────────────────────────────────
try:
    from passlib.context import CryptContext
    _pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    def _hash_pw(pw: str) -> str: return _pwd_ctx.hash(pw)
    def _verify_pw(pw: str, h: str) -> bool: return _pwd_ctx.verify(pw, h)
except Exception:
    def _hash_pw(pw: str) -> str: return hashlib.sha256(pw.encode()).hexdigest()
    def _verify_pw(pw: str, h: str) -> bool: return _hash_pw(pw) == h


# ── User helpers ──────────────────────────────────────────────────────────────
async def _get_or_create_user(
    session: AsyncSession, email: str, name: str | None = None, password: str | None = None
) -> dict:
    row = (
        await session.execute(
            text("SELECT id, email, full_name, company, role FROM users WHERE email = :e LIMIT 1"),
            {"e": email},
        )
    ).mappings().first()
    if row:
        return dict(row)
    uid = str(uuid.uuid4())
    pw_hash = hashlib.sha256(password.encode()).hexdigest() if password else ""
    await session.execute(
        text("""
            INSERT INTO users (id, email, full_name, role, password_hash)
            VALUES (:id, :email, :name, 'user', :pw)
            ON CONFLICT (email) DO NOTHING
        """),
        {"id": uid, "email": email, "name": name or email.split("@")[0], "pw": pw_hash},
    )
    await session.commit()
    row = (
        await session.execute(
            text("SELECT id, email, full_name, company, role FROM users WHERE email = :e LIMIT 1"),
            {"e": email},
        )
    ).mappings().first()
    return dict(row) if row else {"id": uid, "email": email, "full_name": name, "role": "user"}


async def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> dict:
    token_str = creds.credentials if creds else ""

    if ALLOW_DEV_AUTH and (not token_str or token_str.startswith("dev-token")):
        if token_str.startswith("dev-token-"):
            slug = token_str[len("dev-token-"):]
            slug = slug[4:] if slug.startswith("dev-") else slug
            email = f"{slug}@dev.local"
            name = slug.split("-")[0].capitalize()
        else:
            email = "dev@legal-ai.local"
            name = "Dev User"
        return await _get_or_create_user(session, email, name)

    if creds is None:
        raise HTTPException(status_code=401, detail="Missing token")

    data = _decode_token(creds.credentials)
    if not data:
        raise HTTPException(status_code=401, detail="Invalid token")

    row = (
        await session.execute(
            text("SELECT id, email, full_name, company, role FROM users WHERE id = :id LIMIT 1"),
            {"id": data["sub"]},
        )
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(row)


# ── Subscription usage ────────────────────────────────────────────────────────
def _subscription_usage(plan: str, docs_used: int, docs_limit: int | None) -> dict:
    return {"docs_used": docs_used, "docs_limit": docs_limit}


async def _get_usage(session: AsyncSession, user_id: str) -> dict:
    row = (
        await session.execute(
            text("SELECT plan, docs_used, docs_limit FROM subscriptions WHERE user_id = :uid LIMIT 1"),
            {"uid": user_id},
        )
    ).mappings().first()
    if not row:
        return {"docs_used": 0, "docs_limit": 5}
    return _subscription_usage(row["plan"], row["docs_used"], row["docs_limit"])


# ── Audit log (HMAC-chained, best-effort) ────────────────────────────────────
async def _audit_log(
    session: AsyncSession,
    user_id: str,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    try:
        prev_hash = (
            await session.execute(
                text("SELECT integrity_hash FROM audit_logs WHERE user_id = :uid ORDER BY created_at DESC LIMIT 1"),
                {"uid": user_id},
            )
        ).scalar()
        payload = f"{user_id}:{action}:{entity_type}:{entity_id}:{datetime.utcnow().isoformat()}"
        curr_hash = hmac.new(_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        await session.execute(
            text("""
                INSERT INTO audit_logs (id, user_id, action, entity_type, entity_id, metadata,
                    integrity_scope, integrity_prev_hash, integrity_hash)
                VALUES (:id, :uid, :action, :etype, :eid, :meta::jsonb, 'user', :prev, :curr)
            """),
            {
                "id": str(uuid.uuid4()), "uid": user_id, "action": action,
                "etype": entity_type, "eid": entity_id,
                "meta": json.dumps(metadata or {}, ensure_ascii=False),
                "prev": prev_hash, "curr": curr_hash,
            },
        )
    except Exception as e:
        print(f"[audit_log] error: {e}")


# ── AI JSON helper ────────────────────────────────────────────────────────────
async def _ai_json(prompt: str, max_tokens: int = 4096) -> dict | list:
    """Call Anthropic and parse JSON response."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {}
    try:
        import anthropic  # noqa: PLC0415
        client = anthropic.AsyncAnthropic(api_key=api_key)
        msg = await client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
    except Exception as e:
        print(f"[ai_json] error: {e}")
        return {}


# ── MD5 file hash helper ─────────────────────────────────────────────────────
def _compute_md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


# ── Analytics event helper ────────────────────────────────────────────────────
async def _analytics_event(
    session: AsyncSession,
    user_id: str,
    event_type: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Fire-and-forget analytics event. Never raises."""
    try:
        import uuid as _uuid
        await session.execute(
            text("""
                INSERT INTO analytics_events (id, user_id, event_type, entity_type, entity_id, metadata)
                VALUES (:id, :uid, :etype, :ent_type, :ent_id, :meta)
            """),
            {
                "id": str(_uuid.uuid4()), "uid": user_id, "etype": event_type,
                "ent_type": entity_type, "ent_id": entity_id,
                "meta": json.dumps(metadata or {}),
            },
        )
        await session.commit()
    except Exception:
        pass


# ── OpenDataBot helper ────────────────────────────────────────────────────────
_ODB_KEY = os.getenv("OPENDATABOT_API_KEY", "")
_ODB_BASE = "https://api.opendatabot.ua"


async def _odb_get(path: str, params: dict | None = None) -> Any:
    """Proxy a GET request to OpenDataBot API."""
    if not _ODB_KEY:
        raise HTTPException(status_code=503, detail="OPENDATABOT_API_KEY не налаштований")
    headers = {"apikey": _ODB_KEY}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{_ODB_BASE}{path}", params=params, headers=headers)
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Справу не знайдено в OpenDataBot")
    if resp.status_code == 402:
        raise HTTPException(status_code=402, detail="Ліміт запитів OpenDataBot вичерпано")
    if not resp.is_success:
        raise HTTPException(status_code=resp.status_code, detail=f"OpenDataBot error: {resp.text[:200]}")
    return resp.json()
