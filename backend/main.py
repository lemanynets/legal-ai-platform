"""
Legal AI Platform — self-contained FastAPI backend.

All routes are defined here so the build context is just backend/
(no frontend/ copy needed).
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

import asyncio
import pathlib
import time

import httpx
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Base, engine, get_session

# ── Upload directory (ephemeral but safe for single request lifecycle) ─────────
UPLOAD_DIR = pathlib.Path(os.getenv("UPLOAD_DIR", "/tmp/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Legal AI Platform", version="1.0.0")

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://frontend-production-459a.up.railway.app")
ALLOWED_ORIGINS = [
    FRONTEND_URL,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Startup: create tables ────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    try:
        async with engine.begin() as conn:
            # Import models so Base knows about them
            from app.models.user import User  # noqa: F401
            from app.models.case import Case  # noqa: F401
            await conn.run_sync(Base.metadata.create_all)
            # Ensure extra columns exist (idempotent migrations)
            for stmt in _MIGRATIONS:
                try:
                    await conn.execute(text(stmt))
                except Exception:
                    pass
    except Exception as e:
        print(f"[startup] DB init skipped: {e}")

_MIGRATIONS = [
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS company TEXT",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS entity_type TEXT",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS tax_id TEXT",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS address TEXT",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone TEXT",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS logo_url TEXT",
    """CREATE TABLE IF NOT EXISTS subscriptions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        plan TEXT NOT NULL DEFAULT 'FREE',
        docs_used INT NOT NULL DEFAULT 0,
        docs_limit INT,
        period_start TIMESTAMPTZ DEFAULT NOW(),
        period_end TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(user_id)
    )""",
    """CREATE TABLE IF NOT EXISTS generated_documents (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        case_id UUID REFERENCES cases(id) ON DELETE SET NULL,
        document_type TEXT NOT NULL,
        document_category TEXT NOT NULL DEFAULT 'civil',
        title TEXT,
        generated_text TEXT NOT NULL DEFAULT '',
        preview_text TEXT,
        ai_model TEXT,
        used_ai BOOLEAN NOT NULL DEFAULT true,
        has_docx_export BOOLEAN NOT NULL DEFAULT false,
        has_pdf_export BOOLEAN NOT NULL DEFAULT false,
        last_exported_at TIMESTAMPTZ,
        e_court_ready BOOLEAN NOT NULL DEFAULT false,
        filing_blockers JSONB NOT NULL DEFAULT '[]',
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    )""",
    "CREATE INDEX IF NOT EXISTS idx_generated_documents_user_id ON generated_documents(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_generated_documents_created_at ON generated_documents(created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_cases_user_id ON cases(user_id)",
    # ── AI Analyze tables ────────────────────────────────────────────────────
    """CREATE TABLE IF NOT EXISTS contract_analyses (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        file_name TEXT,
        file_url TEXT,
        file_size BIGINT,
        contract_type TEXT,
        risk_level TEXT,
        critical_risks JSONB NOT NULL DEFAULT '[]',
        medium_risks JSONB NOT NULL DEFAULT '[]',
        ok_points JSONB NOT NULL DEFAULT '[]',
        recommendations JSONB NOT NULL DEFAULT '[]',
        summary TEXT,
        ai_model TEXT,
        tokens_used INT,
        processing_time_ms INT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )""",
    "CREATE INDEX IF NOT EXISTS idx_contract_analyses_user_id ON contract_analyses(user_id)",
    """CREATE TABLE IF NOT EXISTS document_intakes (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        case_id UUID REFERENCES cases(id) ON DELETE SET NULL,
        source_file_name TEXT,
        classified_type TEXT NOT NULL DEFAULT 'unknown',
        document_language TEXT,
        jurisdiction TEXT NOT NULL DEFAULT 'UA',
        primary_party_role TEXT,
        identified_parties JSONB NOT NULL DEFAULT '[]',
        subject_matter TEXT,
        financial_exposure_amount NUMERIC,
        financial_exposure_currency TEXT,
        financial_exposure_type TEXT,
        document_date TEXT,
        deadline_from_document TEXT,
        urgency_level TEXT,
        risk_level_legal TEXT,
        risk_level_procedural TEXT,
        risk_level_financial TEXT,
        detected_issues JSONB NOT NULL DEFAULT '[]',
        classifier_confidence NUMERIC,
        classifier_model TEXT,
        raw_text_preview TEXT,
        tags JSONB NOT NULL DEFAULT '[]',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )""",
    "CREATE INDEX IF NOT EXISTS idx_document_intakes_user_id ON document_intakes(user_id)",
    """CREATE TABLE IF NOT EXISTS intake_comments (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        intake_id UUID NOT NULL REFERENCES document_intakes(id) ON DELETE CASCADE,
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        content TEXT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )""",
    "CREATE INDEX IF NOT EXISTS idx_intake_comments_intake_id ON intake_comments(intake_id)",
]

# ── Auth helpers ──────────────────────────────────────────────────────────────
_SECRET = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALLOW_DEV_AUTH = os.getenv("ALLOW_DEV_AUTH", "false").lower() == "true"
_bearer = HTTPBearer(auto_error=False)


def _make_token(user_id: str, email: str) -> str:
    """3-part token: header.payload.sig  (JWT-compatible structure for frontend decoder)."""
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
            # Legacy 2-part format (backward compat)
            payload_b64, sig = parts
            payload_bytes = base64.urlsafe_b64decode(payload_b64.encode() + b"==")
            expected = hmac.new(_SECRET.encode(), payload_bytes, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected):
                return None
            return json.loads(payload_bytes)
    except Exception:
        return None
    return None


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

    # Dev-mode: accept legacy offline tokens (dev-token, dev-token-<slug>)
    if ALLOW_DEV_AUTH and (not token_str or token_str.startswith("dev-token")):
        if token_str.startswith("dev-token-"):
            slug = token_str[len("dev-token-"):]          # e.g. "dev-john"
            # strip leading "dev-" prefix that frontend adds
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


# ── Password helpers ──────────────────────────────────────────────────────────
try:
    from passlib.context import CryptContext
    _pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    def _hash_pw(pw: str) -> str: return _pwd_ctx.hash(pw)
    def _verify_pw(pw: str, h: str) -> bool: return _pwd_ctx.verify(pw, h)
except Exception:
    def _hash_pw(pw: str) -> str: return hashlib.sha256(pw.encode()).hexdigest()
    def _verify_pw(pw: str, h: str) -> bool: return _hash_pw(pw) == h


# ============================================================================
# HEALTH
# ============================================================================
@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


# ============================================================================
# AUTH
# ============================================================================
class AuthRequest(BaseModel):
    email: str
    password: str
    full_name: str | None = None


@app.post("/api/auth/login")
async def login(body: AuthRequest, session: AsyncSession = Depends(get_session)):
    row = (
        await session.execute(
            text("SELECT id, email, full_name, password_hash FROM users WHERE email = :e LIMIT 1"),
            {"e": body.email},
        )
    ).mappings().first()

    if row is None:
        if ALLOW_DEV_AUTH:
            user = await _get_or_create_user(session, body.email, body.email.split("@")[0], body.password)
            token = _make_token(str(user["id"]), body.email)
            return {"access_token": token, "token_type": "bearer",
                    "user": {"id": str(user["id"]), "email": body.email, "name": user.get("full_name")}}
        raise HTTPException(status_code=401, detail="Неправильний email або пароль")

    pw_hash = row.get("password_hash") or ""
    if pw_hash and not _verify_pw(body.password, pw_hash) and not ALLOW_DEV_AUTH:
        raise HTTPException(status_code=401, detail="Неправильний email або пароль")

    token = _make_token(str(row["id"]), body.email)
    return {
        "access_token": token, "token_type": "bearer",
        "user": {"id": str(row["id"]), "email": body.email, "name": row.get("full_name")},
    }


@app.post("/api/auth/register")
async def register(body: AuthRequest, session: AsyncSession = Depends(get_session)):
    exists = (
        await session.execute(text("SELECT 1 FROM users WHERE email = :e LIMIT 1"), {"e": body.email})
    ).first()
    if exists:
        raise HTTPException(status_code=409, detail="Користувач з таким email вже існує")

    uid = str(uuid.uuid4())
    pw_hash = _hash_pw(body.password) if body.password else ""
    await session.execute(
        text("""
            INSERT INTO users (id, email, full_name, role, password_hash)
            VALUES (:id, :email, :name, 'user', :pw)
        """),
        {"id": uid, "email": body.email, "name": body.full_name or body.email.split("@")[0], "pw": pw_hash},
    )
    await session.commit()
    token = _make_token(uid, body.email)
    return {
        "access_token": token, "token_type": "bearer",
        "user": {"id": uid, "email": body.email, "name": body.full_name},
    }


@app.get("/api/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "user_id": str(current_user["id"]),
        "email": current_user["email"],
        "full_name": current_user.get("full_name"),
        "company": current_user.get("company"),
        "role": current_user.get("role", "user"),
        "workspace_id": str(current_user["id"]),
    }


class UpdateMeRequest(BaseModel):
    full_name: str | None = None
    company: str | None = None
    entity_type: str | None = None
    tax_id: str | None = None
    address: str | None = None
    phone: str | None = None
    logo_url: str | None = None


@app.patch("/api/auth/me")
async def update_me(
    body: UpdateMeRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if fields:
        sets = ", ".join(f"{k} = :{k}" for k in fields)
        fields["uid"] = str(current_user["id"])
        await session.execute(text(f"UPDATE users SET {sets} WHERE id = :uid"), fields)
        await session.commit()
    return {"status": "ok"}


# ============================================================================
# BILLING
# ============================================================================
_PLANS = [
    {"id": "FREE",     "name": "FREE",     "price_uah": 0,    "docs_limit": 5,   "features": ["Генерація: 5/міс"]},
    {"id": "PRO",      "name": "PRO",      "price_uah": 499,  "docs_limit": 50,  "features": ["Генерація: 50/міс", "Судова практика"]},
    {"id": "PRO_PLUS", "name": "PRO+",     "price_uah": 999,  "docs_limit": None,"features": ["Безлімітна генерація", "Моніторинг", "Е-Суд"]},
]


@app.get("/api/billing/plans")
async def get_plans():
    return {"items": _PLANS}


@app.get("/api/billing/subscription")
async def get_subscription(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    uid = str(current_user["id"])
    row = (
        await session.execute(
            text("SELECT plan, docs_used, docs_limit FROM subscriptions WHERE user_id = :uid LIMIT 1"),
            {"uid": uid},
        )
    ).mappings().first()

    if row is None:
        # Create default FREE subscription
        try:
            await session.execute(
                text("INSERT INTO subscriptions (user_id, plan, docs_used, docs_limit) VALUES (:uid, 'FREE', 0, 5) ON CONFLICT (user_id) DO NOTHING"),
                {"uid": uid},
            )
            await session.commit()
        except Exception:
            pass
        plan, docs_used, docs_limit = "FREE", 0, 5
    else:
        plan = row["plan"]
        docs_used = row["docs_used"]
        docs_limit = row["docs_limit"]

    return {
        "plan": plan,
        "status": "active",
        "usage": {
            "docs_used": docs_used,
            "docs_limit": docs_limit,
        },
    }


@app.post("/api/billing/subscribe")
async def subscribe_plan(
    body: dict,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    plan = body.get("plan", "FREE")
    limits = {"FREE": 5, "PRO": 50, "PRO_PLUS": None}
    docs_limit = limits.get(plan, 5)
    uid = str(current_user["id"])
    await session.execute(
        text("""
            INSERT INTO subscriptions (user_id, plan, docs_used, docs_limit)
            VALUES (:uid, :plan, 0, :lim)
            ON CONFLICT (user_id) DO UPDATE SET plan = :plan, docs_limit = :lim
        """),
        {"uid": uid, "plan": plan, "lim": docs_limit},
    )
    await session.commit()
    return {"status": "ok", "plan": plan}


# ============================================================================
# DOCUMENTS
# ============================================================================
_DOC_CATEGORIES: dict[str, str] = {
    "pozov_do_sudu": "civil", "pozov_trudovyi": "labor",
    "appeal_complaint": "civil", "dohovir_kupivli_prodazhu": "contract",
    "dohovir_orendi": "contract", "dohovir_nadannia_posluh": "contract",
    "pretenziya": "civil", "dovirennist": "civil",
}

_DOC_LABELS: dict[str, str] = {
    "pozov_do_sudu": "Позов до суду",
    "pozov_trudovyi": "Трудовий позов",
    "appeal_complaint": "Апеляційна скарга",
    "dohovir_kupivli_prodazhu": "Договір купівлі-продажу",
    "dohovir_orendi": "Договір оренди",
    "dohovir_nadannia_posluh": "Договір про надання послуг",
    "pretenziya": "Претензія",
    "dovirennist": "Довіреність",
}


@app.get("/api/documents/types")
async def get_document_types():
    return [
        {"doc_type": k, "title": v, "category": _DOC_CATEGORIES.get(k, "civil"), "procedure": "general"}
        for k, v in _DOC_LABELS.items()
    ]


@app.get("/api/documents/history")
async def get_documents_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    query: str | None = None,
    doc_type: str | None = None,
    case_id: str | None = None,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    uid = str(current_user["id"])
    conditions = ["user_id = :uid"]
    params: dict[str, Any] = {"uid": uid}

    if query:
        conditions.append("(title ILIKE :q OR preview_text ILIKE :q)")
        params["q"] = f"%{query}%"
    if doc_type:
        conditions.append("document_type = :dt")
        params["dt"] = doc_type
    if case_id:
        conditions.append("case_id = :cid")
        params["cid"] = case_id

    where = " AND ".join(conditions)
    order = f"{'created_at' if sort_by not in ('created_at', 'document_type') else sort_by} {'DESC' if sort_dir == 'desc' else 'ASC'}"

    total_row = (await session.execute(text(f"SELECT COUNT(*) FROM generated_documents WHERE {where}"), params)).scalar()
    total = total_row or 0

    params["limit"] = page_size
    params["offset"] = (page - 1) * page_size
    rows = (
        await session.execute(
            text(f"""
                SELECT id, document_type, document_category, title, preview_text,
                       ai_model, used_ai, has_docx_export, has_pdf_export,
                       last_exported_at, e_court_ready, filing_blockers, case_id, created_at
                FROM generated_documents WHERE {where}
                ORDER BY {order} LIMIT :limit OFFSET :offset
            """),
            params,
        )
    ).mappings().all()

    sub_row = (
        await session.execute(
            text("SELECT docs_used, docs_limit FROM subscriptions WHERE user_id = :uid LIMIT 1"),
            {"uid": uid},
        )
    ).mappings().first()

    items = []
    for r in rows:
        items.append({
            "id": str(r["id"]),
            "document_type": r["document_type"],
            "document_category": r.get("document_category", "civil"),
            "title": r.get("title") or _DOC_LABELS.get(r["document_type"], r["document_type"]),
            "generated_text": "",
            "preview_text": r.get("preview_text") or "",
            "ai_model": r.get("ai_model"),
            "used_ai": bool(r.get("used_ai", True)),
            "has_docx_export": bool(r.get("has_docx_export", False)),
            "has_pdf_export": bool(r.get("has_pdf_export", False)),
            "last_exported_at": r.get("last_exported_at"),
            "e_court_ready": bool(r.get("e_court_ready", False)),
            "filing_blockers": r.get("filing_blockers") or [],
            "case_id": str(r["case_id"]) if r.get("case_id") else None,
            "created_at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"]),
        })

    return {
        "user_id": uid,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
        "sort_by": sort_by,
        "sort_dir": sort_dir,
        "query": query,
        "doc_type": doc_type,
        "has_docx_export": None,
        "has_pdf_export": None,
        "items": items,
        "usage": {
            "docs_used": sub_row["docs_used"] if sub_row else 0,
            "docs_limit": sub_row["docs_limit"] if sub_row else 5,
        },
    }


@app.get("/api/documents/{doc_id}")
async def get_document(
    doc_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    row = (
        await session.execute(
            text("SELECT * FROM generated_documents WHERE id = :id AND user_id = :uid LIMIT 1"),
            {"id": doc_id, "uid": str(current_user["id"])},
        )
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    return _doc_row_to_dict(row)


@app.patch("/api/documents/{doc_id}")
async def update_document(
    doc_id: str,
    body: dict,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    uid = str(current_user["id"])
    exists = (
        await session.execute(
            text("SELECT 1 FROM generated_documents WHERE id = :id AND user_id = :uid"), {"id": doc_id, "uid": uid}
        )
    ).first()
    if not exists:
        raise HTTPException(status_code=404, detail="Document not found")

    fields: dict = {}
    if "generated_text" in body:
        fields["generated_text"] = body["generated_text"]
        fields["preview_text"] = body["generated_text"][:200] if body["generated_text"] else ""
    if "case_id" in body:
        fields["case_id"] = body["case_id"]
    if not fields:
        return {"status": "ok", "id": doc_id, "has_docx_export": False, "has_pdf_export": False}

    sets = ", ".join(f"{k} = :{k}" for k in fields)
    fields["id"] = doc_id
    await session.execute(text(f"UPDATE generated_documents SET {sets} WHERE id = :id"), fields)
    await session.commit()
    return {"status": "ok", "id": doc_id, "has_docx_export": False, "has_pdf_export": False}


@app.delete("/api/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(
        text("DELETE FROM generated_documents WHERE id = :id AND user_id = :uid"),
        {"id": doc_id, "uid": str(current_user["id"])},
    )
    await session.commit()
    return {"status": "deleted", "id": doc_id}


def _doc_row_to_dict(r: Any) -> dict:
    return {
        "id": str(r["id"]),
        "document_type": r["document_type"],
        "document_category": r.get("document_category", "civil"),
        "title": r.get("title") or _DOC_LABELS.get(r["document_type"], r["document_type"]),
        "generated_text": r.get("generated_text", ""),
        "preview_text": r.get("preview_text") or "",
        "ai_model": r.get("ai_model"),
        "used_ai": bool(r.get("used_ai", True)),
        "has_docx_export": bool(r.get("has_docx_export", False)),
        "has_pdf_export": bool(r.get("has_pdf_export", False)),
        "last_exported_at": r.get("last_exported_at"),
        "e_court_ready": bool(r.get("e_court_ready", False)),
        "filing_blockers": r.get("filing_blockers") or [],
        "case_id": str(r["case_id"]) if r.get("case_id") else None,
        "created_at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"]),
    }


# ── Document generation ───────────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    doc_type: str
    form_data: dict = {}
    tariff: str = "FREE"
    extra_prompt_context: str | None = None
    case_id: str | None = None
    mode: str | None = None
    style: str | None = None


@app.post("/api/documents/generate")
async def generate_document(
    body: GenerateRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    uid = str(current_user["id"])

    # Check quota
    sub_row = (
        await session.execute(
            text("SELECT plan, docs_used, docs_limit FROM subscriptions WHERE user_id = :uid LIMIT 1"),
            {"uid": uid},
        )
    ).mappings().first()

    docs_used = sub_row["docs_used"] if sub_row else 0
    docs_limit = sub_row["docs_limit"] if sub_row else 5

    if docs_limit is not None and docs_used >= docs_limit:
        raise HTTPException(
            status_code=402,
            detail=f"Ліміт документів вичерпано ({docs_used}/{docs_limit}). Оновіть тариф.",
        )

    # Generate with AI or fallback
    generated_text = await _generate_text(body.doc_type, body.form_data, body.extra_prompt_context)
    preview = generated_text[:200] if generated_text else ""
    doc_title = _DOC_LABELS.get(body.doc_type, body.doc_type.replace("_", " ").title())
    ai_model = "claude-sonnet-4-6"
    doc_id = str(uuid.uuid4())
    category = _DOC_CATEGORIES.get(body.doc_type, "civil")

    await session.execute(
        text("""
            INSERT INTO generated_documents
              (id, user_id, case_id, document_type, document_category, title,
               generated_text, preview_text, ai_model, used_ai, created_at, updated_at)
            VALUES
              (:id, :uid, :cid, :dt, :cat, :title,
               :text, :preview, :model, true, NOW(), NOW())
        """),
        {
            "id": doc_id, "uid": uid, "cid": body.case_id,
            "dt": body.doc_type, "cat": category, "title": doc_title,
            "text": generated_text, "preview": preview, "model": ai_model,
        },
    )

    # Increment usage counter
    await session.execute(
        text("""
            INSERT INTO subscriptions (user_id, plan, docs_used, docs_limit)
            VALUES (:uid, 'FREE', 1, 5)
            ON CONFLICT (user_id) DO UPDATE SET docs_used = subscriptions.docs_used + 1
        """),
        {"uid": uid},
    )
    await session.commit()

    return {
        "status": "generated",
        "id": doc_id,
        "document_type": body.doc_type,
        "document_category": category,
        "title": doc_title,
        "generated_text": generated_text,
        "preview_text": preview,
        "ai_model": ai_model,
        "used_ai": True,
        "has_docx_export": False,
        "has_pdf_export": False,
        "e_court_ready": False,
        "filing_blockers": [],
        "created_at": datetime.utcnow().isoformat(),
    }


async def _generate_text(doc_type: str, form_data: dict, extra_context: str | None) -> str:
    """Generate document text via Anthropic API, falling back to template."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return _template_document(doc_type, form_data)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        label = _DOC_LABELS.get(doc_type, doc_type)
        fields_text = "\n".join(f"  {k}: {v}" for k, v in form_data.items() if v)
        extra = f"\n\nДодатковий контекст: {extra_context}" if extra_context else ""

        prompt = f"""Ти — досвідчений юрист. Склади юридичний документ: {label}.

Дані для документа:
{fields_text}{extra}

Вимоги:
- Документ має бути написаний українською мовою
- Дотримуйся юридичних стандартів і формату
- Включи всі необхідні реквізити
- Документ повинен бути готовим до використання

Надай тільки текст документа без пояснень."""

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception as e:
        print(f"[generate] AI error: {e}")
        return _template_document(doc_type, form_data)


def _template_document(doc_type: str, form_data: dict) -> str:
    """Simple template fallback when AI is unavailable."""
    label = _DOC_LABELS.get(doc_type, doc_type.replace("_", " ").title())
    plaintiff = form_data.get("plaintiff_name") or form_data.get("party_name") or form_data.get("name") or "[Ім'я]"
    defendant = form_data.get("defendant_name") or form_data.get("counterparty") or "[Відповідач]"
    description = form_data.get("description") or form_data.get("claim_description") or form_data.get("subject") or "[Опис]"
    amount = form_data.get("amount") or form_data.get("claim_amount") or ""
    date = datetime.utcnow().strftime("%d.%m.%Y")

    return f"""{label.upper()}

Дата складення: {date}

СТОРОНИ:
Позивач / Сторона 1: {plaintiff}
Відповідач / Сторона 2: {defendant}

СУТЬ ЗВЕРНЕННЯ:
{description}
{f"Сума вимоги: {amount} грн." if amount else ""}

На підставі вищевикладеного прошу задовольнити вимоги в повному обсязі.

Дата: {date}
Підпис: _______________
"""


# ============================================================================
# CASES
# ============================================================================
@app.get("/api/cases")
async def get_cases(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    uid = str(current_user["id"])
    rows = (
        await session.execute(
            text("""
                SELECT id, user_id, title, description, case_number, status, created_at, updated_at
                FROM cases WHERE user_id = :uid ORDER BY created_at DESC
            """),
            {"uid": uid},
        )
    ).mappings().all()
    return [_case_row(r) for r in rows]


@app.post("/api/cases", status_code=201)
async def create_case(
    body: dict,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    uid = str(current_user["id"])
    case_id = str(uuid.uuid4())
    now = datetime.utcnow()
    await session.execute(
        text("""
            INSERT INTO cases (id, user_id, title, description, case_number, status, created_at, updated_at)
            VALUES (:id, :uid, :title, :desc, :num, :status, :now, :now)
        """),
        {
            "id": case_id, "uid": uid,
            "title": body.get("title", "Без назви"),
            "desc": body.get("description"),
            "num": body.get("case_number"),
            "status": body.get("status", "open"),
            "now": now,
        },
    )
    await session.commit()
    row = (
        await session.execute(
            text("SELECT * FROM cases WHERE id = :id LIMIT 1"), {"id": case_id}
        )
    ).mappings().first()
    return _case_row(row)


@app.get("/api/cases/{case_id}")
async def get_case(
    case_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    row = (
        await session.execute(
            text("SELECT * FROM cases WHERE id = :id AND user_id = :uid LIMIT 1"),
            {"id": case_id, "uid": str(current_user["id"])},
        )
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")

    docs = (
        await session.execute(
            text("SELECT id, document_type, document_category, created_at FROM generated_documents WHERE case_id = :cid ORDER BY created_at DESC"),
            {"cid": case_id},
        )
    ).mappings().all()

    result = _case_row(row)
    result["documents"] = [
        {"id": str(d["id"]), "document_type": d["document_type"],
         "document_category": d.get("document_category", "civil"),
         "created_at": d["created_at"].isoformat() if hasattr(d["created_at"], "isoformat") else str(d["created_at"])}
        for d in docs
    ]
    result["forum_posts"] = []
    result["case_law_items"] = []
    return result


@app.patch("/api/cases/{case_id}")
async def update_case(
    case_id: str,
    body: dict,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    uid = str(current_user["id"])
    allowed = {"title", "description", "case_number", "status"}
    fields = {k: v for k, v in body.items() if k in allowed}
    if fields:
        fields["updated_at"] = datetime.utcnow()
        sets = ", ".join(f"{k} = :{k}" for k in fields)
        fields["id"] = case_id
        fields["uid"] = uid
        await session.execute(
            text(f"UPDATE cases SET {sets} WHERE id = :id AND user_id = :uid"), fields
        )
        await session.commit()
    row = (
        await session.execute(
            text("SELECT * FROM cases WHERE id = :id AND user_id = :uid LIMIT 1"),
            {"id": case_id, "uid": uid},
        )
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    return _case_row(row)


@app.delete("/api/cases/{case_id}")
async def delete_case(
    case_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(
        text("DELETE FROM cases WHERE id = :id AND user_id = :uid"),
        {"id": case_id, "uid": str(current_user["id"])},
    )
    await session.commit()
    return {"status": "deleted"}


def _case_row(r: Any) -> dict:
    return {
        "id": str(r["id"]),
        "user_id": str(r["user_id"]),
        "title": r["title"],
        "description": r.get("description"),
        "case_number": r.get("case_number"),
        "status": r.get("status", "open"),
        "created_at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"]),
        "updated_at": r["updated_at"].isoformat() if hasattr(r.get("updated_at"), "isoformat") else str(r.get("updated_at", r["created_at"])),
    }


# ============================================================================
# GLOBAL SEARCH
# ============================================================================
@app.get("/api/dashboard/search")
async def global_search(
    q: str = Query(..., min_length=2),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    uid = str(current_user["id"])
    pattern = f"%{q}%"

    cases = (
        await session.execute(
            text("SELECT id, title, case_number FROM cases WHERE user_id = :uid AND title ILIKE :q LIMIT 5"),
            {"uid": uid, "q": pattern},
        )
    ).mappings().all()

    docs = (
        await session.execute(
            text("SELECT id, document_type, preview_text FROM generated_documents WHERE user_id = :uid AND (title ILIKE :q OR preview_text ILIKE :q) LIMIT 5"),
            {"uid": uid, "q": pattern},
        )
    ).mappings().all()

    return {
        "cases": [{"id": str(c["id"]), "title": c["title"], "number": c.get("case_number")} for c in cases],
        "documents": [{"id": str(d["id"]), "type": d["document_type"], "preview": d.get("preview_text", "")} for d in docs],
        "forum": [],
    }


# ============================================================================
# STUB ENDPOINTS (return empty/default so frontend doesn't break)
# ============================================================================
@app.get("/api/documents/form-schema/{doc_type}")
async def get_form_schema(doc_type: str):
    return {"fields": []}


@app.get("/api/billing/invoices")
async def get_invoices(current_user: dict = Depends(get_current_user)):
    return {"items": []}


@app.get("/api/team/users")
async def get_team_users(current_user: dict = Depends(get_current_user)):
    return {"items": [{"id": str(current_user["id"]), "email": current_user["email"], "role": current_user.get("role", "user")}]}


@app.get("/api/deadlines")
async def get_deadlines(current_user: dict = Depends(get_current_user)):
    return {"items": []}


@app.post("/api/deadlines")
async def create_deadline(body: dict, current_user: dict = Depends(get_current_user)):
    return {"id": str(uuid.uuid4()), **body, "user_id": str(current_user["id"]), "created_at": datetime.utcnow().isoformat()}


@app.get("/api/case-law/search")
async def search_case_law(q: str = Query(""), current_user: dict = Depends(get_current_user)):
    return {"items": [], "total": 0, "query": q}


@app.get("/api/case-law/digest")
async def get_case_law_digest(current_user: dict = Depends(get_current_user)):
    return {"items": []}


@app.get("/api/knowledge-base")
async def get_knowledge_base(current_user: dict = Depends(get_current_user)):
    return {"items": []}


@app.get("/api/registries/watch")
async def get_registry_watch(current_user: dict = Depends(get_current_user)):
    return {"items": []}


@app.get("/api/monitoring/status")
async def get_monitoring_status(current_user: dict = Depends(get_current_user)):
    return {"status": "inactive"}


@app.get("/api/reports")
async def get_reports(current_user: dict = Depends(get_current_user)):
    return {"items": []}


@app.get("/api/calculations/history")
async def get_calculation_history(current_user: dict = Depends(get_current_user)):
    return {"items": []}


@app.post("/api/calculations/full-claim")
async def calculate_full_claim(body: dict, current_user: dict = Depends(get_current_user)):
    return {"status": "ok", "result": {}}


@app.get("/api/audit/history")
async def get_audit_history(current_user: dict = Depends(get_current_user)):
    return {"items": [], "total": 0}


# ============================================================================
# AI ANALYZE  (/api/analyze/*)
# ============================================================================

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


async def _run_ai_intake(
    file_bytes: bytes,
    file_name: str,
    jurisdiction: str,
    mode: str,
    api_key: str | None,
) -> dict:
    """Call Anthropic API for deep document intake analysis."""
    if not api_key:
        return _demo_intake(file_name, jurisdiction)

    try:
        import anthropic  # noqa: PLC0415

        client = anthropic.AsyncAnthropic(api_key=api_key)
        text_preview = file_bytes.decode("utf-8", errors="replace")[:10000]
        max_tokens = 4096 if mode == "deep" else 2048

        prompt = f"""Ти — юридичний аналітик. Проаналізуй такий документ і поверни ТІЛЬКИ валідний JSON без markdown та додаткового тексту.

Документ (перші символи):
{text_preview}

Поверни JSON з такими полями:
{{
  "classified_type": "рядок (договір/позов/рішення/судовий наказ/інше)",
  "document_language": "uk або en або інше",
  "primary_party_role": "позивач/відповідач/кредитор/боржник/інше або null",
  "identified_parties": [{{"role": "...", "name": "..."}}],
  "subject_matter": "короткий опис предмету (1-2 речення)",
  "financial_exposure_amount": число або null,
  "financial_exposure_currency": "UAH/USD/EUR або null",
  "financial_exposure_type": "борг/штраф/компенсація або null",
  "document_date": "YYYY-MM-DD або null",
  "deadline_from_document": "YYYY-MM-DD або null",
  "urgency_level": "low/medium/high/critical",
  "risk_level_legal": "low/medium/high/critical",
  "risk_level_procedural": "low/medium/high/critical",
  "risk_level_financial": "low/medium/high/critical",
  "detected_issues": [
    {{"issue_type": "...", "severity": "low/medium/high/critical", "description": "...", "impact": "..."}}
  ],
  "classifier_confidence": число від 0 до 1,
  "tags": ["рядок", ...]
}}"""

        message = await client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
    except Exception as e:
        print(f"[analyze] AI error: {e}")
        return _demo_intake(file_name, jurisdiction)


def _demo_intake(file_name: str, jurisdiction: str) -> dict:
    return {
        "classified_type": "контракт",
        "document_language": "uk",
        "primary_party_role": None,
        "identified_parties": [],
        "subject_matter": f"[Demo] Файл: {file_name}. Налаштуйте ANTHROPIC_API_KEY для реального аналізу.",
        "financial_exposure_amount": None,
        "financial_exposure_currency": None,
        "financial_exposure_type": None,
        "document_date": None,
        "deadline_from_document": None,
        "urgency_level": "medium",
        "risk_level_legal": "medium",
        "risk_level_procedural": "low",
        "risk_level_financial": "low",
        "detected_issues": [
            {
                "issue_type": "demo",
                "severity": "low",
                "description": "Demo режим — API ключ не налаштовано",
                "impact": "Додайте ANTHROPIC_API_KEY у змінні оточення Railway",
            }
        ],
        "classifier_confidence": 0.0,
        "tags": ["demo"],
    }


def _intake_row_to_dict(row: Any, usage: dict) -> dict:
    r = dict(row)
    for field in ("identified_parties", "detected_issues", "tags"):
        if isinstance(r.get(field), str):
            try:
                r[field] = json.loads(r[field])
            except Exception:
                r[field] = []
    r["usage"] = usage
    r["cache_hit"] = False
    return r


@app.post("/api/analyze/intake")
async def analyze_intake(
    file: UploadFile = File(...),
    jurisdiction: str = Form("UA"),
    case_id: str = Form(None),
    mode: str = Query("standard"),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    t0 = time.monotonic()
    uid = str(current_user["id"])

    # Read file bytes (no disk write needed — ephemeral containers)
    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Не вдалося прочитати файл: {e}")

    file_name = file.filename or "document"
    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")

    ai_result = await _run_ai_intake(file_bytes, file_name, jurisdiction, mode, api_key)

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    rid = str(uuid.uuid4())

    await session.execute(
        text("""
            INSERT INTO document_intakes (
                id, user_id, case_id, source_file_name,
                classified_type, document_language, jurisdiction,
                primary_party_role, identified_parties, subject_matter,
                financial_exposure_amount, financial_exposure_currency, financial_exposure_type,
                document_date, deadline_from_document, urgency_level,
                risk_level_legal, risk_level_procedural, risk_level_financial,
                detected_issues, classifier_confidence, classifier_model,
                raw_text_preview, tags
            ) VALUES (
                :id, :uid, :case_id, :fname,
                :ctype, :lang, :jur,
                :role, :parties::jsonb, :subject,
                :amount, :currency, :exp_type,
                :doc_date, :deadline, :urgency,
                :rl_legal, :rl_proc, :rl_fin,
                :issues::jsonb, :conf, :model,
                :preview, :tags::jsonb
            )
        """),
        {
            "id": rid,
            "uid": uid,
            "case_id": case_id or None,
            "fname": file_name,
            "ctype": ai_result.get("classified_type", "unknown"),
            "lang": ai_result.get("document_language"),
            "jur": jurisdiction,
            "role": ai_result.get("primary_party_role"),
            "parties": json.dumps(ai_result.get("identified_parties", []), ensure_ascii=False),
            "subject": ai_result.get("subject_matter"),
            "amount": ai_result.get("financial_exposure_amount"),
            "currency": ai_result.get("financial_exposure_currency"),
            "exp_type": ai_result.get("financial_exposure_type"),
            "doc_date": ai_result.get("document_date"),
            "deadline": ai_result.get("deadline_from_document"),
            "urgency": ai_result.get("urgency_level", "medium"),
            "rl_legal": ai_result.get("risk_level_legal", "medium"),
            "rl_proc": ai_result.get("risk_level_procedural", "low"),
            "rl_fin": ai_result.get("risk_level_financial", "low"),
            "issues": json.dumps(ai_result.get("detected_issues", []), ensure_ascii=False),
            "conf": ai_result.get("classifier_confidence"),
            "model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6") if api_key else "demo",
            "preview": file_bytes.decode("utf-8", errors="replace")[:500],
            "tags": json.dumps(ai_result.get("tags", []), ensure_ascii=False),
        },
    )
    await session.commit()

    usage = await _get_usage(session, uid)
    row = (
        await session.execute(
            text("SELECT * FROM document_intakes WHERE id = :id LIMIT 1"), {"id": rid}
        )
    ).mappings().first()
    return _intake_row_to_dict(row, usage)


@app.post("/api/analyze/intake-stream")
async def analyze_intake_stream(
    file: UploadFile = File(...),
    jurisdiction: str = Form("UA"),
    case_id: str = Form(None),
    mode: str = Query("standard"),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """SSE streaming wrapper — runs intake and emits one `result` event."""
    file_bytes = await file.read()
    file_name = file.filename or "document"
    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")
    uid = str(current_user["id"])

    async def event_stream():
        yield "data: " + json.dumps({"event": "start", "message": "Аналіз розпочато…"}) + "\n\n"
        await asyncio.sleep(0)

        ai_result = await _run_ai_intake(file_bytes, file_name, jurisdiction, mode, api_key)
        rid = str(uuid.uuid4())

        try:
            await session.execute(
                text("""
                    INSERT INTO document_intakes (
                        id, user_id, case_id, source_file_name,
                        classified_type, document_language, jurisdiction,
                        primary_party_role, identified_parties, subject_matter,
                        financial_exposure_amount, financial_exposure_currency, financial_exposure_type,
                        document_date, deadline_from_document, urgency_level,
                        risk_level_legal, risk_level_procedural, risk_level_financial,
                        detected_issues, classifier_confidence, classifier_model,
                        raw_text_preview, tags
                    ) VALUES (
                        :id, :uid, :case_id, :fname,
                        :ctype, :lang, :jur,
                        :role, :parties::jsonb, :subject,
                        :amount, :currency, :exp_type,
                        :doc_date, :deadline, :urgency,
                        :rl_legal, :rl_proc, :rl_fin,
                        :issues::jsonb, :conf, :model,
                        :preview, :tags::jsonb
                    )
                """),
                {
                    "id": rid, "uid": uid, "case_id": case_id or None, "fname": file_name,
                    "ctype": ai_result.get("classified_type", "unknown"),
                    "lang": ai_result.get("document_language"), "jur": jurisdiction,
                    "role": ai_result.get("primary_party_role"),
                    "parties": json.dumps(ai_result.get("identified_parties", []), ensure_ascii=False),
                    "subject": ai_result.get("subject_matter"),
                    "amount": ai_result.get("financial_exposure_amount"),
                    "currency": ai_result.get("financial_exposure_currency"),
                    "exp_type": ai_result.get("financial_exposure_type"),
                    "doc_date": ai_result.get("document_date"),
                    "deadline": ai_result.get("deadline_from_document"),
                    "urgency": ai_result.get("urgency_level", "medium"),
                    "rl_legal": ai_result.get("risk_level_legal", "medium"),
                    "rl_proc": ai_result.get("risk_level_procedural", "low"),
                    "rl_fin": ai_result.get("risk_level_financial", "low"),
                    "issues": json.dumps(ai_result.get("detected_issues", []), ensure_ascii=False),
                    "conf": ai_result.get("classifier_confidence"),
                    "model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6") if api_key else "demo",
                    "preview": file_bytes.decode("utf-8", errors="replace")[:500],
                    "tags": json.dumps(ai_result.get("tags", []), ensure_ascii=False),
                },
            )
            await session.commit()
        except Exception as e:
            print(f"[intake-stream] DB error: {e}")

        usage = await _get_usage(session, uid)
        row = (await session.execute(
            text("SELECT * FROM document_intakes WHERE id = :id LIMIT 1"), {"id": rid}
        )).mappings().first()
        result = _intake_row_to_dict(row, usage) if row else {"id": rid, "usage": usage}
        yield "data: " + json.dumps({"event": "result", "result": result}) + "\n\n"
        yield "data: " + json.dumps({"event": "done"}) + "\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/analyze/history")
async def get_analyze_history(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    uid = str(current_user["id"])
    rows = (
        await session.execute(
            text("SELECT * FROM contract_analyses WHERE user_id = :uid ORDER BY created_at DESC LIMIT 50"),
            {"uid": uid},
        )
    ).mappings().all()
    usage = await _get_usage(session, uid)
    items = []
    for r in rows:
        d = dict(r)
        for f in ("critical_risks", "medium_risks", "ok_points", "recommendations"):
            if isinstance(d.get(f), str):
                try:
                    d[f] = json.loads(d[f])
                except Exception:
                    d[f] = []
        d["usage"] = usage
        items.append(d)
    return {"total": len(items), "items": items, "usage": usage}


@app.post("/api/analyze/process")
async def process_contract_analysis(
    body: dict,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    uid = str(current_user["id"])
    t0 = time.monotonic()
    contract_text = body.get("contract_text", "")
    file_name = body.get("file_name", "document.txt")
    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")

    from app.services.intake_analyzer import run_intake_analysis  # noqa: PLC0415
    result = await run_intake_analysis(
        contract_text.encode("utf-8"),
        file_name,
        body.get("mode"),
    )
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    rid = str(uuid.uuid4())
    await session.execute(
        text("""
            INSERT INTO contract_analyses (
                id, user_id, file_name, file_url, file_size,
                risk_level, critical_risks, medium_risks, ok_points,
                recommendations, summary, ai_model, tokens_used, processing_time_ms
            ) VALUES (
                :id, :uid, :fname, :furl, :fsize,
                :rl, :cr::jsonb, :mr::jsonb, :ok::jsonb,
                :rec::jsonb, :summary, :model, :tokens, :ms
            )
        """),
        {
            "id": rid, "uid": uid, "fname": file_name,
            "furl": body.get("file_url"), "fsize": body.get("file_size"),
            "rl": result.get("risk_level", "medium"),
            "cr": json.dumps(result.get("critical_risks", []), ensure_ascii=False),
            "mr": json.dumps(result.get("medium_risks", []), ensure_ascii=False),
            "ok": json.dumps(result.get("ok_points", []), ensure_ascii=False),
            "rec": json.dumps(result.get("recommendations", []), ensure_ascii=False),
            "summary": result.get("summary"),
            "model": result.get("ai_model", "demo"),
            "tokens": result.get("tokens_used", 0),
            "ms": elapsed_ms,
        },
    )
    await session.commit()
    usage = await _get_usage(session, uid)
    return {
        "id": rid,
        "user_id": uid,
        "file_name": file_name,
        "file_url": body.get("file_url"),
        "file_size": body.get("file_size"),
        "contract_type": None,
        "risk_level": result.get("risk_level", "medium"),
        "critical_risks": result.get("critical_risks", []),
        "medium_risks": result.get("medium_risks", []),
        "ok_points": result.get("ok_points", []),
        "recommendations": result.get("recommendations", []),
        "summary": result.get("summary"),
        "ai_model": result.get("ai_model", "demo"),
        "tokens_used": result.get("tokens_used", 0),
        "processing_time_ms": elapsed_ms,
        "tags": [],
        "created_at": datetime.utcnow().isoformat(),
        "usage": usage,
    }


@app.get("/api/analyze/{analysis_id}")
async def get_analysis(
    analysis_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    uid = str(current_user["id"])
    usage = await _get_usage(session, uid)

    # Try document_intakes first
    row = (
        await session.execute(
            text("SELECT * FROM document_intakes WHERE id = :id AND user_id = :uid LIMIT 1"),
            {"id": analysis_id, "uid": uid},
        )
    ).mappings().first()
    if row:
        return _intake_row_to_dict(row, usage)

    # Fallback to contract_analyses
    row = (
        await session.execute(
            text("SELECT * FROM contract_analyses WHERE id = :id AND user_id = :uid LIMIT 1"),
            {"id": analysis_id, "uid": uid},
        )
    ).mappings().first()
    if row:
        d = dict(row)
        d["usage"] = usage
        return d

    raise HTTPException(status_code=404, detail="Аналіз не знайдено")


@app.patch("/api/analyze/{analysis_id}")
async def update_analysis(
    analysis_id: str,
    body: dict,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    uid = str(current_user["id"])
    allowed = {"classified_type", "subject_matter", "urgency_level", "risk_level_legal",
                "risk_level_procedural", "risk_level_financial", "tags"}
    fields = {k: v for k, v in body.items() if k in allowed and v is not None}
    if fields:
        sets = ", ".join(f"{k} = :{k}" for k in fields)
        if "tags" in fields:
            fields["tags"] = json.dumps(fields["tags"], ensure_ascii=False)
            sets = sets.replace("tags = :tags", "tags = :tags::jsonb")
        fields.update({"id": analysis_id, "uid": uid})
        await session.execute(
            text(f"UPDATE document_intakes SET {sets} WHERE id = :id AND user_id = :uid"),
            fields,
        )
        await session.commit()
    return {"status": "ok"}


@app.post("/api/analyze/gdpr-check")
async def gdpr_check(
    body: dict,
    current_user: dict = Depends(get_current_user),
):
    text_content = body.get("text", "")
    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")

    if not api_key:
        return {
            "report": "[Demo] GDPR-перевірка потребує ANTHROPIC_API_KEY",
            "compliant": True,
            "issues": [],
            "personal_data_found": [],
            "recommendations": ["Налаштуйте ANTHROPIC_API_KEY у Railway"],
        }

    try:
        import anthropic  # noqa: PLC0415
        client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        prompt = (
            f"Проаналізуй текст на GDPR-відповідність і поверни JSON:\n"
            f"{{'compliant': bool, 'report': '...', 'issues': [...], "
            f"'personal_data_found': [{{'type': '...', 'count': N}}], "
            f"'recommendations': [...]}}\n\nТекст:\n{text_content[:5000]}"
        )
        msg = await client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
    except Exception as e:
        return {
            "report": f"Помилка аналізу: {e}",
            "compliant": True,
            "issues": [],
            "personal_data_found": [],
            "recommendations": [],
        }


@app.get("/api/analyze/{intake_id}/comments")
async def get_intake_comments(
    intake_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        await session.execute(
            text("""
                SELECT c.id, c.intake_id, c.user_id, u.full_name as user_name, c.content, c.created_at
                FROM intake_comments c
                LEFT JOIN users u ON u.id = c.user_id
                WHERE c.intake_id = :iid
                ORDER BY c.created_at ASC
            """),
            {"iid": intake_id},
        )
    ).mappings().all()
    return [dict(r) for r in rows]


@app.post("/api/analyze/{intake_id}/comments")
async def create_intake_comment(
    intake_id: str,
    body: dict,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    uid = str(current_user["id"])
    cid = str(uuid.uuid4())
    content = body.get("content", "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Порожній коментар")
    await session.execute(
        text("INSERT INTO intake_comments (id, intake_id, user_id, content) VALUES (:id, :iid, :uid, :content)"),
        {"id": cid, "iid": intake_id, "uid": uid, "content": content},
    )
    await session.commit()
    return {
        "id": cid,
        "intake_id": intake_id,
        "user_id": uid,
        "user_name": current_user.get("full_name"),
        "content": content,
        "created_at": datetime.utcnow().isoformat(),
    }


@app.delete("/api/analyze/{intake_id}/comments/{comment_id}")
async def delete_intake_comment(
    intake_id: str,
    comment_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    uid = str(current_user["id"])
    await session.execute(
        text("DELETE FROM intake_comments WHERE id = :cid AND intake_id = :iid AND user_id = :uid"),
        {"cid": comment_id, "iid": intake_id, "uid": uid},
    )
    await session.commit()
    return {"status": "ok"}


@app.post("/api/analyze/{intake_id}/precedent-map")
async def create_precedent_map(
    intake_id: str,
    limit: int = Query(10),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    # Stub — returns empty map (real precedent search requires vector DB)
    return {
        "intake_id": intake_id,
        "query_used": "",
        "groups": [],
        "refs": [],
    }


# ── OpenDataBot proxy ─────────────────────────────────────────────────────────

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


@app.get("/api/opendatabot/court-cases/{case_number}")
async def get_court_case(
    case_number: str,
    judgment_code: int | None = Query(None),
    current_user: dict = Depends(get_current_user),
):
    params: dict = {"number": case_number}
    if judgment_code:
        params["judgment_code"] = judgment_code
    data = await _odb_get("/v1/court/case", params=params)
    return data


@app.get("/api/opendatabot/usage")
async def get_opendatabot_usage(current_user: dict = Depends(get_current_user)):
    if not _ODB_KEY:
        return {"limit": 0, "used": 0, "remaining": 0, "expires_at": None, "api_url": _ODB_BASE}
    data = await _odb_get("/v1/account/usage")
    return {
        "limit": data.get("limit", 0),
        "used": data.get("used", 0),
        "remaining": data.get("remaining", 0),
        "expires_at": data.get("expires_at"),
        "api_url": _ODB_BASE,
    }


@app.get("/api/opendatabot/company/{code}")
async def get_company(code: str, current_user: dict = Depends(get_current_user)):
    data = await _odb_get(f"/v1/company/{code}")
    return data


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "false").lower() == "true",
    )
