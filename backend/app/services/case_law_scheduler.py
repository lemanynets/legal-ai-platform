from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging

from sqlalchemy import desc, select

from app.config import settings
from app.database import SessionLocal
from app.models import Subscription
from app.services.audit import log_action
from app.services.case_law_cache import get_case_law_digest, sync_case_law_sources
from app.services.case_law_digests import save_case_law_digest


logger = logging.getLogger("case_law_scheduler")
AUTO_DIGEST_PLANS = {"PRO", "PRO_PLUS"}


def _run_sync_once() -> None:
    with SessionLocal() as db:
        query = settings.case_law_auto_sync_query or None
        limit = settings.case_law_auto_sync_limit
        sources = [item.strip().lower() for item in settings.case_law_auto_sync_sources.split(",") if item.strip()]
        try:
            stats = sync_case_law_sources(
                db,
                query=query,
                limit=limit,
                sources=sources,
                allow_seed_fallback=settings.case_law_allow_seed_fallback,
            )
            log_action(
                db,
                user_id=None,
                action="case_law_sync_auto",
                entity_type="case_law_cache",
                entity_id=None,
                metadata={
                    "query": query,
                    "limit": limit,
                    "created": stats.created,
                    "updated": stats.updated,
                    "total": stats.total,
                    "sources": stats.used_sources,
                    "seed_fallback_used": stats.seed_fallback_used,
                    "fetched_counts": stats.fetched_counts,
                },
            )
            logger.info(
                "Case law auto-sync completed: created=%s updated=%s total=%s",
                stats.created,
                stats.updated,
                stats.total,
            )
        except Exception as exc:
            try:
                log_action(
                    db,
                    user_id=None,
                    action="case_law_sync_auto_failed",
                    entity_type="case_law_cache",
                    entity_id=None,
                    metadata={"query": query, "limit": limit, "error": str(exc)},
                )
            except Exception:
                logger.exception("Failed to write auto-sync failure audit entry")
            raise


async def run_case_law_sync_loop(stop_event: asyncio.Event) -> None:
    interval_seconds = max(60, settings.case_law_auto_sync_interval_minutes * 60)

    if settings.case_law_auto_sync_run_on_start and not stop_event.is_set():
        try:
            _run_sync_once()
        except Exception:
            logger.exception("Case law auto-sync failed on startup")

    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
            break
        except asyncio.TimeoutError:
            try:
                _run_sync_once()
            except Exception:
                logger.exception("Case law auto-sync failed in loop")


def _run_digest_once() -> None:
    with SessionLocal() as db:
        users_seen: set[str] = set()
        created = 0
        skipped = 0
        failed = 0
        stmt = select(Subscription).order_by(Subscription.user_id.asc(), desc(Subscription.created_at))
        rows = list(db.execute(stmt).scalars().all())
        for subscription in rows:
            user_id = subscription.user_id
            if user_id in users_seen:
                continue
            users_seen.add(user_id)
            if subscription.plan not in AUTO_DIGEST_PLANS or subscription.status != "active":
                skipped += 1
                continue
            try:
                digest = get_case_law_digest(
                    db,
                    days=settings.case_law_digest_auto_days,
                    limit=settings.case_law_digest_auto_limit,
                    court_type=None,
                    sources=None,
                    only_supreme=settings.case_law_digest_auto_only_supreme,
                )
                generated_at = datetime.now(timezone.utc).isoformat()
                title = f"Auto weekly digest {datetime.now(timezone.utc).date().isoformat()}"
                saved = save_case_law_digest(
                    db,
                    user_id=user_id,
                    rows=digest.items,
                    days=digest.days,
                    limit=digest.limit,
                    only_supreme=digest.only_supreme,
                    court_type=digest.court_type,
                    sources=digest.sources,
                    total=digest.total,
                    generated_at=generated_at,
                    title=title,
                )
                created += 1
                log_action(
                    db,
                    user_id=user_id,
                    action="case_law_digest_auto",
                    entity_type="case_law_digest",
                    entity_id=saved.id,
                    metadata={
                        "plan": subscription.plan,
                        "days": digest.days,
                        "limit": digest.limit,
                        "only_supreme": digest.only_supreme,
                        "total": digest.total,
                        "item_count": len(digest.items),
                    },
                )
            except Exception as exc:
                failed += 1
                try:
                    log_action(
                        db,
                        user_id=user_id,
                        action="case_law_digest_auto_failed",
                        entity_type="case_law_digest",
                        entity_id=None,
                        metadata={"plan": subscription.plan, "error": str(exc)},
                    )
                except Exception:
                    logger.exception("Failed to write auto-digest failure audit entry")
                logger.exception("Case law auto-digest failed for user %s", user_id)

        logger.info(
            "Case law auto-digest completed: users=%s created=%s skipped=%s failed=%s",
            len(users_seen),
            created,
            skipped,
            failed,
        )


async def run_case_law_digest_loop(stop_event: asyncio.Event) -> None:
    interval_seconds = max(3600, settings.case_law_digest_auto_interval_hours * 3600)

    if settings.case_law_digest_auto_run_on_start and not stop_event.is_set():
        try:
            _run_digest_once()
        except Exception:
            logger.exception("Case law auto-digest failed on startup")

    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
            break
        except asyncio.TimeoutError:
            try:
                _run_digest_once()
            except Exception:
                logger.exception("Case law auto-digest failed in loop")
