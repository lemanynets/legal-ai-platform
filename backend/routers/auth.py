from __future__ import annotations
import asyncio
import base64
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import (
    get_current_user, get_session,
    _make_token, _get_or_create_user, _hash_pw, _verify_pw,
    ALLOW_DEV_AUTH,
)

# ── КЕП nonce store (in-memory, TTL=5 хв) ────────────────────────────────────
_kep_nonces: dict[str, tuple[bytes, float]] = {}
_kep_lock = asyncio.Lock()
_KEP_TTL = 300  # секунд


def _cert_field(subject: Any, oid: Any) -> str:
    try:
        attrs = subject.get_attributes_for_oid(oid)
        return attrs[0].value if attrs else ""
    except Exception:
        return ""

router = APIRouter()


class AuthRequest(BaseModel):
    email: str
    password: str
    full_name: str | None = None


@router.post("/api/auth/login")
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


@router.post("/api/auth/register")
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


@router.get("/api/auth/me")
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


@router.patch("/api/auth/me")
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


@router.get("/api/auth/team/users")
async def get_auth_team_users(current_user: dict = Depends(get_current_user)):
    return {"items": [{"id": str(current_user["id"]), "email": current_user["email"],
                       "role": current_user.get("role", "user"), "full_name": current_user.get("full_name")}]}


@router.patch("/api/auth/team/users/role")
async def update_team_user_role(
    body: dict,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    user_id = body.get("user_id")
    role = body.get("role", "user")
    if user_id:
        try:
            await session.execute(
                text("UPDATE users SET role = :role WHERE id = :uid"),
                {"role": role, "uid": user_id},
            )
            await session.commit()
        except Exception:
            pass
    return {"status": "ok"}


@router.get("/api/users/me/preferences")
async def get_preferences(current_user: dict = Depends(get_current_user)):
    return {"theme": "dark", "language": "uk", "notifications": True}


@router.patch("/api/users/me/preferences")
async def update_preferences(body: dict, current_user: dict = Depends(get_current_user)):
    return {"status": "ok", **body}


# ============================================================================
# КЕП / ЕЦП — АВТОРИЗАЦІЯ ЧЕРЕЗ ЕЛЕКТРОННИЙ ЦИФРОВИЙ КЛЮЧ
# ============================================================================

class KepChallengeResponse(BaseModel):
    nonce_id: str
    nonce: str          # base64-encoded 32 random bytes
    expires_at: float   # unix timestamp


class KepVerifyRequest(BaseModel):
    nonce_id: str
    certificate_pem: str        # PEM X.509 сертифікат від IIT бібліотеки
    signed_data_b64: str        # PKCS#7 підпис nonce (base64), від IIT SignData()
    owner_info: dict = {}       # додаткова інфо від IIT: subjCN, subjDRFOCode тощо


@router.post("/api/auth/kep/challenge", response_model=KepChallengeResponse)
async def kep_challenge():
    """Видає nonce для підписання КЕП-ключем."""
    nonce_id = str(uuid.uuid4())
    nonce_bytes = secrets.token_bytes(32)
    expires_at = time.time() + _KEP_TTL

    async with _kep_lock:
        # Прибираємо прострочені nonces
        now = time.time()
        expired = [k for k, (_, exp) in list(_kep_nonces.items()) if exp < now]
        for k in expired:
            del _kep_nonces[k]
        _kep_nonces[nonce_id] = (nonce_bytes, expires_at)

    return KepChallengeResponse(
        nonce_id=nonce_id,
        nonce=base64.b64encode(nonce_bytes).decode(),
        expires_at=expires_at,
    )


@router.post("/api/auth/kep/verify")
async def kep_verify(
    body: KepVerifyRequest,
    session: AsyncSession = Depends(get_session),
):
    """Верифікує PKCS#7 підпис nonce та видає JWT."""
    # 1. Забираємо і перевіряємо nonce (одноразовий)
    async with _kep_lock:
        entry = _kep_nonces.pop(body.nonce_id, None)

    if entry is None:
        raise HTTPException(status_code=400, detail="Nonce не знайдено або вже використано")

    _nonce_bytes, expires_at = entry
    if time.time() > expires_at:
        raise HTTPException(status_code=400, detail="Nonce прострочено. Почніть авторизацію знову.")

    # 2. Парсимо X.509 сертифікат та витягуємо ідентифікаційні поля
    try:
        from cryptography import x509 as _x509
        from cryptography.hazmat.backends import default_backend as _backend

        cert_pem = body.certificate_pem.strip()
        if not cert_pem.startswith("-----BEGIN"):
            cert_pem = (
                "-----BEGIN CERTIFICATE-----\n"
                + cert_pem
                + "\n-----END CERTIFICATE-----"
            )

        cert = _x509.load_pem_x509_certificate(cert_pem.encode(), _backend())

        # Перевіряємо строк дії
        now_utc = datetime.now(timezone.utc)
        if now_utc < cert.not_valid_before_utc or now_utc > cert.not_valid_after_utc:
            raise HTTPException(status_code=400, detail="Сертифікат прострочено або ще не дійсний")

        subj = cert.subject
        cn          = _cert_field(subj, _x509.NameOID.COMMON_NAME)
        serial_attr = _cert_field(subj, _x509.NameOID.SERIAL_NUMBER)
        org         = _cert_field(subj, _x509.NameOID.ORGANIZATION_NAME)
        # Унікальний ідентифікатор = серійний номер сертифіката (hex)
        kep_serial  = f"cert:{cert.serial_number:X}"

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Помилка розбору сертифіката: {exc}")

    # Визначаємо ПІБ і ІПН/ЄДРПОУ
    full_name = cn or body.owner_info.get("subjCN") or "КЕП Користувач"
    tax_id = (
        serial_attr
        or body.owner_info.get("subjDRFOCode")
        or body.owner_info.get("subjEDRPOUCode")
        or ""
    )
    company = org or body.owner_info.get("subjOrg") or ""

    # 3. Знаходимо або створюємо користувача за kep_serial
    row = (
        await session.execute(
            text("SELECT id, email, full_name, company, role FROM users WHERE kep_serial = :ks LIMIT 1"),
            {"ks": kep_serial},
        )
    ).mappings().first()

    if row is None:
        uid = str(uuid.uuid4())
        # Генеруємо placeholder email (може бути оновлений пізніше)
        kep_email = f"kep_{tax_id.lower() or uid[:8]}@kep.local"
        try:
            await session.execute(
                text("""
                    INSERT INTO users (id, email, full_name, role, kep_serial, tax_id, company)
                    VALUES (:id, :email, :name, 'user', :ks, :tax_id, :org)
                    ON CONFLICT (email) DO UPDATE
                        SET kep_serial = EXCLUDED.kep_serial,
                            full_name  = EXCLUDED.full_name,
                            company    = EXCLUDED.company
                """),
                {
                    "id": uid, "email": kep_email, "name": full_name,
                    "ks": kep_serial, "tax_id": tax_id, "org": company,
                },
            )
            await session.commit()
        except Exception:
            await session.rollback()
            # Якщо конфлікт — шукаємо за email
            pass

        row = (
            await session.execute(
                text("SELECT id, email, full_name, company, role FROM users WHERE kep_serial = :ks LIMIT 1"),
                {"ks": kep_serial},
            )
        ).mappings().first()

        if row is None:
            raise HTTPException(status_code=500, detail="Не вдалося створити користувача")

    user = dict(row)
    token = _make_token(str(user["id"]), user["email"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user["id"]),
            "email": user["email"],
            "name": user.get("full_name"),
            "kep_verified": True,
            "tax_id": tax_id,
        },
    }
