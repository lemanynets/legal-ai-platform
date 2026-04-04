from __future__ import annotations
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import (
    get_current_user, get_session,
    _make_token, _get_or_create_user, _hash_pw, _verify_pw,
    ALLOW_DEV_AUTH,
)

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
