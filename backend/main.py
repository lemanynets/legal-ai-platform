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
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Base, engine, get_session

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
    if ALLOW_DEV_AUTH and (creds is None or creds.credentials in ("dev-token", "")):
        return await _get_or_create_user(session, "dev@legal-ai.local", "Dev User")

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "false").lower() == "true",
    )
