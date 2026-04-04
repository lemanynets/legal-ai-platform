from __future__ import annotations

import asyncio
import logging

from sqlalchemy import desc, select

from app.config import settings
from app.database import SessionLocal
from app.models import Subscription
from app.services.audit import log_action
from app.services.entitlements import PLAN_RANK
from app.services.registry_monitoring import check_due_watch_items


logger = logging.getLogger("registry_monitor_scheduler")
AUTO_MIN_PLAN_RANK = PLAN_RANK.get("PRO_PLUS", 3)


def _is_subscription_eligible(subscription: Subscription) -> bool:
    status_ok = (subscription.status or "").strip().lower() == "active"
    rank = PLAN_RANK.get((subscription.plan or "").strip().upper(), -1)
    return status_ok and rank >= AUTO_MIN_PLAN_RANK


def _run_registry_monitor_once() -> None:
    with SessionLocal() as db:
        users_seen: set[str] = set()
        processed = 0
        skipped = 0
        checked_total = 0
        changed_total = 0

        rows = list(
            db.execute(select(Subscription).order_by(Subscription.user_id.asc(), desc(Subscription.created_at))).scalars().all()
        )
        for subscription in rows:
            user_id = subscription.user_id
            if user_id in users_seen:
                continue
            users_seen.add(user_id)
            if not _is_subscription_eligible(subscription):
                skipped += 1
                continue
            processed += 1
            stats = check_due_watch_items(
                db,
                user_id=user_id,
                limit=settings.registry_monitor_auto_check_limit,
                auto=True,
            )
            checked_total += stats.checked
            changed_total += stats.state_changed
            if stats.scanned > 0:
                log_action(
                    db,
                    user_id=user_id,
                    action="registry_check_due_auto",
                    entity_type="registry_watch_item",
                    entity_id=None,
                    metadata={
                        "limit": settings.registry_monitor_auto_check_limit,
                        "scanned": stats.scanned,
                        "checked": stats.checked,
                        "state_changed": stats.state_changed,
                    },
                )

        log_action(
            db,
            user_id=None,
            action="registry_check_due_auto_summary",
            entity_type="registry_watch_item",
            entity_id=None,
            metadata={
                "users_total": len(users_seen),
                "processed": processed,
                "skipped": skipped,
                "checked_total": checked_total,
                "state_changed_total": changed_total,
            },
        )
        logger.info(
            "Registry monitor auto-check done: users_total=%s processed=%s skipped=%s checked=%s changed=%s",
            len(users_seen),
            processed,
            skipped,
            checked_total,
            changed_total,
        )


async def run_registry_monitor_loop(stop_event: asyncio.Event) -> None:
    interval_seconds = max(60, settings.registry_monitor_auto_interval_minutes * 60)

    if settings.registry_monitor_auto_run_on_start and not stop_event.is_set():
        try:
            _run_registry_monitor_once()
        except Exception:
            logger.exception("Registry monitor auto-check failed on startup")

    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
            break
        except asyncio.TimeoutError:
            try:
                _run_registry_monitor_once()
            except Exception:
                logger.exception("Registry monitor auto-check failed in loop")
