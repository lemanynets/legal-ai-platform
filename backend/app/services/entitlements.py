from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.models import Subscription
from app.services.access_control import ensure_user_role
from app.services.subscriptions import get_or_create_subscription


PLAN_RANK: dict[str, int] = {
    "FREE": 0,
    "START": 1,
    "PRO": 2,
    "PRO_PLUS": 3,
    "TEAM": 4,
}

FEATURE_MIN_PLAN: dict[str, str] = {
    "case_law_saved_digests": "PRO",
    "case_law_import": "PRO_PLUS",
    "case_law_sync": "PRO_PLUS",
    "case_law_monitoring": "PRO_PLUS",
    "e_court_submission": "PRO_PLUS",
    "e_court_history": "PRO_PLUS",
    "registry_monitoring": "PRO_PLUS",
}

FEATURE_ALLOWED_ROLES: dict[str, set[str]] = {
    "case_law_saved_digests": {"owner", "admin", "lawyer", "analyst", "viewer"},
    "case_law_import": {"owner", "admin", "lawyer", "analyst"},
    "case_law_sync": {"owner", "admin", "analyst"},
    "case_law_monitoring": {"owner", "admin", "lawyer", "analyst"},
    "e_court_submission": {"owner", "admin", "lawyer"},
    "e_court_history": {"owner", "admin", "lawyer", "analyst", "viewer"},
    "registry_monitoring": {"owner", "admin", "lawyer", "analyst"},
}


def _plan_rank(plan: str | None) -> int:
    code = (plan or "").strip().upper()
    return PLAN_RANK.get(code, -1)


def ensure_feature_access(
    db: Session,
    *,
    current_user: CurrentUser,
    feature: str,
) -> Subscription:
    min_plan = FEATURE_MIN_PLAN.get(feature)
    if not min_plan:
        raise HTTPException(status_code=500, detail=f"Unknown feature entitlement: {feature}")

    allowed_roles = FEATURE_ALLOWED_ROLES.get(feature)
    if allowed_roles:
        ensure_user_role(
            db,
            current_user=current_user,
            allowed_roles=allowed_roles,
            reason=f"feature '{feature}'",
        )

    subscription = get_or_create_subscription(db, current_user)
    status = (subscription.status or "").strip().lower()
    if status != "active":
        raise HTTPException(status_code=402, detail="Subscription is not active. Complete payment to access this feature.")

    if _plan_rank(subscription.plan) < _plan_rank(min_plan):
        raise HTTPException(
            status_code=403,
            detail=f"Feature '{feature}' requires at least {min_plan} plan. Current plan: {subscription.plan}.",
        )
    return subscription
