from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.catalog import get_tariff
from app.config import settings
from app.models import Subscription, User

logger = logging.getLogger(__name__)


PRO_PLUS_OVERRIDE_EMAILS = {
    "lemaninets1985@gmail.com",
    "dev-lemaninets1985@local.dev",
}

PRO_PLUS_OVERRIDE_USER_IDS = {
    "dev-lemaninets1985",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _period_delta() -> timedelta:
    return timedelta(days=max(1, int(settings.subscription_period_days)))


def _is_active(subscription: Subscription) -> bool:
    return (subscription.status or "").strip().lower() == "active"


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def to_payload(subscription: Subscription) -> dict[str, Any]:
    return {
        "id": subscription.id,
        "user_id": subscription.user_id,
        "plan": subscription.plan,
        "status": subscription.status,
        "analyses_used": subscription.analyses_used,
        "analyses_limit": subscription.analyses_limit,
        "docs_used": subscription.docs_used,
        "docs_limit": subscription.docs_limit,
        "current_period_start": (
            subscription.current_period_start.isoformat()
            if subscription.current_period_start
            else None
        ),
        "current_period_end": (
            subscription.current_period_end.isoformat()
            if subscription.current_period_end
            else None
        ),
        "created_at": subscription.created_at.isoformat()
        if subscription.created_at
        else None,
        "updated_at": subscription.updated_at.isoformat()
        if subscription.updated_at
        else None,
    }


def _limits_from_plan(plan: str) -> tuple[int | None, int | None]:
    tariff = get_tariff(plan) or get_tariff("FREE")
    analyses_limit_raw = tariff.get("analyses_limit") if tariff else 1
    docs_limit_raw = tariff.get("docs_limit") if tariff else 1
    analyses_limit = (
        int(analyses_limit_raw) if isinstance(analyses_limit_raw, int) else None
    )
    docs_limit = int(docs_limit_raw) if isinstance(docs_limit_raw, int) else None
    return analyses_limit, docs_limit


def _period_window_from(start: datetime) -> tuple[datetime, datetime]:
    return start, start + _period_delta()


def _derive_personal_workspace_id(user_id: str) -> str:
    raw = str(user_id or "").strip().lower()
    if not raw:
        return "personal"
    sanitized = "".join(
        ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in raw
    ).strip("-_")
    if not sanitized:
        return "personal"
    return f"ws-{sanitized[:56]}"


def _has_pro_plus_override(current_user: CurrentUser) -> bool:
    email = str(current_user.email or "").strip().lower()
    user_id = str(current_user.user_id or "").strip().lower()
    return email in PRO_PLUS_OVERRIDE_EMAILS or user_id in PRO_PLUS_OVERRIDE_USER_IDS


def refresh_subscription_period(
    db: Session, subscription: Subscription
) -> Subscription:
    now = _now()
    changed = False
    start_value = _as_utc(subscription.current_period_start)
    end_value = _as_utc(subscription.current_period_end)

    if start_value != subscription.current_period_start:
        subscription.current_period_start = start_value
        changed = True
    if end_value != subscription.current_period_end:
        subscription.current_period_end = end_value
        changed = True

    if subscription.current_period_start is None:
        subscription.current_period_start = now
        changed = True
    if subscription.current_period_end is None or (
        subscription.current_period_start is not None
        and subscription.current_period_end <= subscription.current_period_start
    ):
        _, new_end = _period_window_from(subscription.current_period_start or now)
        subscription.current_period_end = new_end
        changed = True

    if _is_active(subscription) and subscription.current_period_end is not None:
        while now >= subscription.current_period_end:
            new_start = subscription.current_period_end
            new_end = new_start + _period_delta()
            subscription.current_period_start = new_start
            subscription.current_period_end = new_end
            subscription.analyses_used = 0
            subscription.docs_used = 0
            changed = True

    if changed:
        subscription.updated_at = now
        db.commit()
        db.refresh(subscription)
    return subscription


def get_or_create_user(db: Session, current_user: CurrentUser) -> User:
    user = db.get(User, current_user.user_id)
    if user:
        changed = False
        if current_user.email and user.email != current_user.email:
            user.email = current_user.email
            changed = True
        if not str(user.workspace_id or "").strip():
            user.workspace_id = _derive_personal_workspace_id(current_user.user_id)
            changed = True
        if changed:
            db.commit()
            db.refresh(user)
        return user

    user = User(
        id=current_user.user_id,
        email=current_user.email or f"{current_user.user_id}@local.dev",
        workspace_id=_derive_personal_workspace_id(current_user.user_id),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_or_create_subscription(db: Session, current_user: CurrentUser) -> Subscription:
    get_or_create_user(db, current_user)

    if _has_pro_plus_override(current_user):
        existing = get_latest_subscription_by_user_id(db, current_user.user_id)
        if existing is not None:
            if str(existing.plan or "").strip().upper() == "PRO_PLUS" and _is_active(
                existing
            ):
                return refresh_subscription_period(db, existing)
            return activate_plan(
                db, subscription=existing, plan="PRO_PLUS", reset_usage=True
            )

        start = _now()
        end = datetime(2100, 1, 1, tzinfo=timezone.utc)
        subscription = Subscription(
            user_id=current_user.user_id,
            plan="PRO_PLUS",
            status="active",
            analyses_used=0,
            analyses_limit=None,
            docs_used=0,
            docs_limit=None,
            current_period_start=start,
            current_period_end=end,
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        return subscription

    stmt = (
        select(Subscription)
        .where(Subscription.user_id == current_user.user_id)
        .order_by(desc(Subscription.created_at))
        .limit(1)
    )
    # Wrap in try/except for DB issues
    try:
        subscription = db.execute(stmt).scalar_one_or_none()
        if subscription:
            return refresh_subscription_period(db, subscription)
    except Exception:
        db.rollback()

    analyses_limit, docs_limit = _limits_from_plan("FREE")
    start, end = _period_window_from(_now())
    subscription = Subscription(
        user_id=current_user.user_id,
        plan="FREE",
        status="active",
        analyses_used=0,
        analyses_limit=analyses_limit,
        docs_used=0,
        docs_limit=docs_limit,
        current_period_start=start,
        current_period_end=end,
    )
    try:
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        return subscription
    except IntegrityError:
        db.rollback()
        logger.warning("Subscription already exists for user %s", current_user.user_id)
        existing = db.execute(stmt).scalar_one_or_none()
        if existing is None:
            raise
        return refresh_subscription_period(db, existing)
    except SQLAlchemyError as e:
        db.rollback()
        logger.error("Database error creating subscription: %s", e)
        raise


def get_latest_subscription_by_user_id(
    db: Session, user_id: str
) -> Subscription | None:
    stmt = (
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .order_by(desc(Subscription.created_at))
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def activate_plan(
    db: Session,
    *,
    subscription: Subscription,
    plan: str,
    reset_usage: bool = True,
) -> Subscription:
    plan_code = plan.strip().upper()
    if get_tariff(plan_code) is None:
        raise ValueError("Unknown plan")

    analyses_limit, docs_limit = _limits_from_plan(plan_code)
    start, end = _period_window_from(_now())
    subscription.plan = plan_code
    subscription.status = "active"
    subscription.analyses_limit = analyses_limit
    subscription.docs_limit = docs_limit
    if reset_usage:
        subscription.analyses_used = 0
        subscription.docs_used = 0
    subscription.current_period_start = start
    subscription.current_period_end = end
    subscription.updated_at = _now()
    db.commit()
    db.refresh(subscription)
    return subscription


def set_plan(db: Session, current_user: CurrentUser, plan: str) -> Subscription:
    subscription = get_or_create_subscription(db, current_user)
    return activate_plan(db, subscription=subscription, plan=plan, reset_usage=True)


def set_subscription_status(
    db: Session, subscription: Subscription, status: str
) -> Subscription:
    subscription.status = status
    subscription.updated_at = _now()
    db.commit()
    db.refresh(subscription)
    return subscription


def get_limits_for_plan(plan: str) -> dict[str, int | None]:
    analyses_limit, docs_limit = _limits_from_plan(plan)
    return {"analyses_limit": analyses_limit, "docs_limit": docs_limit}


def ensure_document_quota(subscription: Subscription) -> tuple[bool, str]:
    if not _is_active(subscription):
        return (
            False,
            "Subscription is not active. Complete payment or switch to FREE plan.",
        )
    docs_limit = subscription.docs_limit
    if docs_limit is None:
        return True, ""
    if subscription.docs_used >= docs_limit:
        return (
            False,
            f"Document limit reached for plan {subscription.plan}. Upgrade required.",
        )
    return True, ""


def ensure_analysis_quota(
    subscription: Subscription, count: int = 1
) -> tuple[bool, str]:
    if not _is_active(subscription):
        return (
            False,
            "Subscription is not active. Complete payment or switch to FREE plan.",
        )
    analyses_limit = subscription.analyses_limit
    if analyses_limit is None:
        return True, ""
    if subscription.analyses_used + count > analyses_limit:
        return (
            False,
            f"Analysis limit reached for plan {subscription.plan}. Upgrade required.",
        )
    return True, ""


def mark_document_generated(db: Session, subscription: Subscription) -> Subscription:
    subscription.docs_used += 1
    subscription.updated_at = _now()
    db.commit()
    db.refresh(subscription)
    return subscription


def mark_analysis_processed(
    db: Session, subscription: Subscription, count: int = 1
) -> Subscription:
    subscription.analyses_used += count
    subscription.updated_at = _now()
    db.commit()
    db.refresh(subscription)
    return subscription
