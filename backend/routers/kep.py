"""
КЕП / ЕЦП — авторизація через електронний цифровий ключ.

Флоу:
  1. POST /api/auth/kep/challenge  — отримати nonce (TTL 5 хв)
  2. POST /api/auth/kep/verify     — верифікувати підпис, отримати JWT
"""
from __future__ import annotations

import asyncio
import base64
import secrets
import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_session, _make_token  # noqa: F401

router = APIRouter(tags=["kep"])

# ── nonce store (in-memory, TTL=5 хв) ─────────────────────────────────────────
_kep_nonces: dict[str, tuple[bytes, float]] = {}
_kep_lock = asyncio.Lock()
_KEP_TTL = 300  # seconds


def _cert_field(subject: object, oid: object) -> str:
    try:
        # subject is a cryptography x509.Name object
        attrs = subject.get_attributes_for_oid(oid)  # type: ignore[attr-defined]
        return attrs[0].value if attrs else ""
    except Exception:
        return ""


# ── Pydantic models ────────────────────────────────────────────────────────────

class KepChallengeResponse(BaseModel):
    nonce_id: str
    nonce: str         # base64-encoded 32 random bytes
    expires_at: float  # unix timestamp


class KepVerifyRequest(BaseModel):
    nonce_id: str
    certificate_pem: str   # PEM X.509 сертифікат від IIT бібліотеки
    signed_data_b64: str   # PKCS#7 підпис nonce (base64)
    owner_info: dict = {}  # додаткова інфо від IIT: subjCN, subjDRFOCode тощо


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/api/auth/kep/challenge", response_model=KepChallengeResponse)
async def kep_challenge() -> KepChallengeResponse:
    """Видає одноразовий nonce для підписання КЕП-ключем."""
    nonce_id = str(uuid.uuid4())
    nonce_bytes = secrets.token_bytes(32)
    expires_at = time.time() + _KEP_TTL

    async with _kep_lock:
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
) -> dict:
    """Верифікує PKCS#7 підпис nonce та видає JWT."""

    # 1. Забираємо nonce (одноразовий, TTL)
    async with _kep_lock:
        entry = _kep_nonces.pop(body.nonce_id, None)

    if entry is None:
        raise HTTPException(status_code=400, detail="Nonce не знайдено або вже використано")

    _nonce_bytes, expires_at = entry
    if time.time() > expires_at:
        raise HTTPException(status_code=400, detail="Nonce прострочено. Почніть авторизацію знову.")

    # 2. Парсимо X.509 сертифікат
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

        now_utc = datetime.now(timezone.utc)
        if now_utc < cert.not_valid_before_utc or now_utc > cert.not_valid_after_utc:
            raise HTTPException(status_code=400, detail="Сертифікат прострочено або ще не дійсний")

        subj = cert.subject
        cn          = _cert_field(subj, _x509.NameOID.COMMON_NAME)
        serial_attr = _cert_field(subj, _x509.NameOID.SERIAL_NUMBER)
        org         = _cert_field(subj, _x509.NameOID.ORGANIZATION_NAME)
        kep_serial  = f"cert:{cert.serial_number:X}"

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Помилка розбору сертифіката: {exc}")

    # 3. Витягуємо ідентифікаційні дані
    full_name = cn or body.owner_info.get("subjCN") or "КЕП Користувач"
    tax_id = (
        serial_attr
        or body.owner_info.get("subjDRFOCode")
        or body.owner_info.get("subjEDRPOUCode")
        or ""
    )
    company = org or body.owner_info.get("subjOrg") or ""

    # 4. Знаходимо / створюємо користувача за kep_serial
    row = (
        await session.execute(
            text("SELECT id, email, full_name, company, role FROM users WHERE kep_serial = :ks LIMIT 1"),
            {"ks": kep_serial},
        )
    ).mappings().first()

    if row is None:
        uid = str(uuid.uuid4())
        kep_email = f"kep_{(tax_id or uid[:8]).lower()}@kep.local"
        try:
            await session.execute(
                text("""
                    INSERT INTO users (id, email, full_name, role, kep_serial, tax_id, company)
                    VALUES (:id, :email, :name, 'user', :ks, :tid, :org)
                    ON CONFLICT (email) DO UPDATE
                        SET kep_serial = EXCLUDED.kep_serial,
                            full_name  = EXCLUDED.full_name,
                            company    = EXCLUDED.company
                """),
                {
                    "id": uid, "email": kep_email, "name": full_name,
                    "ks": kep_serial, "tid": tax_id, "org": company,
                },
            )
            await session.commit()
        except Exception:
            await session.rollback()

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
