from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_session

router = APIRouter()

_PLANS = [
    {"id": "FREE",     "name": "FREE",     "price_uah": 0,    "docs_limit": 5,   "features": ["Генерація: 5/міс"]},
    {"id": "PRO",      "name": "PRO",      "price_uah": 499,  "docs_limit": 50,  "features": ["Генерація: 50/міс", "Судова практика"]},
    {"id": "PRO_PLUS", "name": "PRO+",     "price_uah": 999,  "docs_limit": None,"features": ["Безлімітна генерація", "Моніторинг", "Е-Суд"]},
]


@router.get("/api/billing/plans")
async def get_plans():
    return {"items": _PLANS}


@router.get("/api/billing/subscription")
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


@router.post("/api/billing/subscribe")
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


@router.get("/api/billing/invoices")
async def get_invoices(current_user: dict = Depends(get_current_user)):
    return {"items": []}
