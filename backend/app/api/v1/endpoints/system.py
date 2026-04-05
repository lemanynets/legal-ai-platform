from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["system"])


@router.get("/health")
async def health_v1() -> dict[str, str]:
    return {"status": "ok", "version": settings.app_version, "environment": settings.environment}
