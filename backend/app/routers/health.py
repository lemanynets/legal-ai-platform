from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db: Session = Depends(get_db)) -> dict[str, Any]:
    checks: dict[str, bool] = {"database": False, "ai_providers": False}

    try:
        db.execute(select(func.count()).select_from(User)).scalar_one()
        checks["database"] = True
    except Exception:
        pass

    checks["ai_providers"] = bool(settings.openai_api_key or settings.anthropic_api_key or settings.gemini_api_key)

    status = "ok" if checks["database"] else "degraded"
    return {
        "status": status,
        "checks": checks,
        "ready": bool(checks["database"] and checks["ai_providers"]),
    }
