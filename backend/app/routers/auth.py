from __future__ import annotations

import re
import uuid
from typing import Any
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, field_validator
from slowapi import Limiter
from app.services.rate_limiting import get_user_or_ip_key
from sqlalchemy import asc, func, select
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.models import User
from app.schemas import (
    TeamUserRoleUpdateRequest,
    TeamUserRoleUpdateResponse,
    TeamUsersResponse,
)
from app.services.audit import log_action
from app.services.access_control import normalize_role
from app.services.subscriptions import get_or_create_user
from app.services.security import verify_password, get_password_hash, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])
auth_limiter = Limiter(key_func=get_user_or_ip_key)


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    company: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Пароль має містити мінімум 8 символів")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Пароль має містити хоча б одну велику літеру")
        if not re.search(r"[0-9]", v):
            raise ValueError("Пароль має містити хоча б одну цифру")
        return v

class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str


@router.post("/register", response_model=TokenResponse)
@auth_limiter.limit("5/minute")
def auth_register(request: Request, payload: UserRegister, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    existing_user = db.execute(select(User).where(User.email == email)).scalar()
    if existing_user:
        raise HTTPException(status_code=400, detail="Користувач з такою поштою вже існує")
        
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(payload.password)
    
    new_user = User(
        id=user_id,
        email=email,
        full_name=payload.full_name,
        company=payload.company,
        hashed_password=hashed_password,
        role="owner",
        workspace_id=user_id, # personal workspace
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = create_access_token(
        data={"sub": new_user.id, "email": new_user.email},
        expires_delta=timedelta(days=7)
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login", response_model=TokenResponse)
@auth_limiter.limit("10/minute")
def auth_login(request: Request, payload: UserLogin, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    user = db.execute(select(User).where(User.email == email)).scalar()
    
    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неправильний email або пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неправильний email або пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email},
        expires_delta=timedelta(days=7)
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
def auth_me(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    profile = get_or_create_user(db, user)
    normalized_role = normalize_role(profile.role)
    log_action(
        db,
        user_id=user.user_id,
        action="auth_me",
        entity_type="user",
        entity_id=user.user_id,
        metadata={
            "workspace_id": profile.workspace_id,
            "role": normalized_role,
        },
    )
    return {
        "user_id": user.user_id,
        "email": user.email,
        "workspace_id": profile.workspace_id,
        "role": normalized_role,
        "full_name": profile.full_name,
        "company": profile.company,
        "logo_url": profile.logo_url if profile.logo_url != "None" else None,
        "entity_type": profile.entity_type,
        "tax_id": profile.tax_id,
        "address": profile.address,
        "phone": profile.phone,
    }

from typing import Any

from pydantic import BaseModel

class ProfileUpdate(BaseModel):
    logo_url: str | None = None
    full_name: str | None = None
    company: str | None = None
    entity_type: str | None = None
    tax_id: str | None = None
    address: str | None = None
    phone: str | None = None

@router.patch("/me")
def update_auth_me(
    payload: ProfileUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    profile = get_or_create_user(db, user)
    
    update_data = payload.dict(exclude_unset=True)
    if "logo_url" in update_data:
        profile.logo_url = update_data["logo_url"]
    if "full_name" in update_data:
        profile.full_name = update_data["full_name"]
    if "company" in update_data:
        profile.company = update_data["company"]
    if "entity_type" in update_data:
        profile.entity_type = update_data["entity_type"]
    if "tax_id" in update_data:
        profile.tax_id = update_data["tax_id"]
    if "address" in update_data:
        profile.address = update_data["address"]
    if "phone" in update_data:
        profile.phone = update_data["phone"]
        
    for k in ["logo_url", "full_name", "company", "tax_id", "address", "phone", "entity_type"]:
        if getattr(profile, k) == "None":
            setattr(profile, k, None)
            
    db.commit()
    db.refresh(profile)
    return {"status": "ok"}


def _serialize_team_user(user: User) -> dict[str, str | None]:
    return {
        "user_id": user.id,
        "email": user.email,
        "workspace_id": user.workspace_id,
        "role": normalize_role(user.role),
        "full_name": user.full_name,
        "company": user.company,
        "created_at": user.created_at.isoformat(),
    }


@router.get("/team/users", response_model=TeamUsersResponse)
def auth_team_users(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TeamUsersResponse:
    actor = get_or_create_user(db, user)
    actor_role = normalize_role(actor.role)
    if actor_role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Team management requires owner or admin role.")

    rows = list(
        db.execute(
            select(User)
            .where(User.workspace_id == actor.workspace_id)
            .order_by(asc(User.created_at), asc(User.id))
        )
        .scalars()
        .all()
    )
    total = int(
        db.execute(select(func.count()).select_from(User).where(User.workspace_id == actor.workspace_id)).scalar_one()
        or 0
    )
    log_action(
        db,
        user_id=user.user_id,
        action="auth_team_users_list",
        entity_type="user",
        metadata={
            "workspace_id": actor.workspace_id,
            "actor_role": actor_role,
            "returned": len(rows),
            "total": total,
        },
    )
    return TeamUsersResponse(
        workspace_id=actor.workspace_id,
        actor_role=actor_role,
        total=total,
        items=[_serialize_team_user(item) for item in rows],
    )


@router.post("/team/users/role", response_model=TeamUserRoleUpdateResponse)
def auth_team_user_role_update(
    payload: TeamUserRoleUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TeamUserRoleUpdateResponse:
    actor = get_or_create_user(db, user)
    actor_role = normalize_role(actor.role)
    if actor_role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Role updates require owner or admin role.")

    requested_role = normalize_role(payload.role)
    allowed_roles = {"owner", "admin", "lawyer", "analyst", "viewer"}
    if requested_role not in allowed_roles:
        raise HTTPException(status_code=422, detail=f"Unsupported role: {requested_role}.")
    if actor_role == "admin" and requested_role in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Admin cannot assign owner/admin roles.")

    target_user_id = payload.target_user_id.strip()
    if not target_user_id:
        raise HTTPException(status_code=422, detail="target_user_id is required")

    target = db.get(User, target_user_id)
    if target is not None:
        if target.workspace_id != actor.workspace_id:
            raise HTTPException(status_code=403, detail="Target user belongs to another workspace.")
        if actor_role == "admin" and normalize_role(target.role) in {"owner", "admin"}:
            raise HTTPException(status_code=403, detail="Admin cannot update owner/admin users.")
        target.role = requested_role
        if payload.email and payload.email.strip():
            target.email = payload.email.strip()
        if payload.full_name is not None:
            target.full_name = payload.full_name.strip() or None
        if payload.company is not None:
            target.company = payload.company.strip() or None
    else:
        email = (payload.email or "").strip() or f"{target_user_id}@local.dev"
        target = User(
            id=target_user_id,
            email=email,
            workspace_id=actor.workspace_id,
            role=requested_role,
            full_name=(payload.full_name or "").strip() or None,
            company=(payload.company or "").strip() or None,
        )
        db.add(target)

    db.commit()
    db.refresh(target)
    log_action(
        db,
        user_id=user.user_id,
        action="auth_team_user_role_update",
        entity_type="user",
        entity_id=target.id,
        metadata={
            "workspace_id": actor.workspace_id,
            "actor_role": actor_role,
            "target_role": normalize_role(target.role),
        },
    )
    return TeamUserRoleUpdateResponse(status="ok", item=_serialize_team_user(target))
