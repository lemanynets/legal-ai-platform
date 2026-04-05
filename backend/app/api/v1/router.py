from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints.system import router as system_router

api_v1_router = APIRouter()
api_v1_router.include_router(system_router, prefix="/system")
