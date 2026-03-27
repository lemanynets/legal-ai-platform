"""
Content-hash based caching for intake analysis results.

Cache key: SHA-256(file_bytes) + user_id + jurisdiction + mode
TTL: 30 days (configurable via INTAKE_CACHE_TTL_DAYS env var).

Avoids repeated LLM calls when the same user uploads the same file
with the same analysis parameters.
"""

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


CACHE_TTL_DAYS = int(os.environ.get("INTAKE_CACHE_TTL_DAYS", "30"))


def compute_content_hash(file_bytes: bytes) -> str:
    """Compute SHA-256 hex digest of raw file bytes."""
    return hashlib.sha256(file_bytes).hexdigest()


async def lookup_cached_analysis(
    session: AsyncSession,
    *,
    user_id: UUID,
    content_hash: str,
    jurisdiction: str,
    mode: str,
) -> Optional[dict[str, Any]]:
    """
    Look up a cached analysis result.

    Returns the cached result dict if found and not expired, else None.
    """
    row = (
        await session.execute(
            text("""
                SELECT id, result, created_at
                FROM intake_analysis_cache
                WHERE user_id = :user_id
                  AND content_hash = :content_hash
                  AND jurisdiction = :jurisdiction
                  AND mode = :mode
                  AND expires_at > NOW()
                ORDER BY created_at DESC
                LIMIT 1
            """),
            {
                "user_id": user_id,
                "content_hash": content_hash,
                "jurisdiction": jurisdiction,
                "mode": mode,
            },
        )
    ).first()

    if row is None:
        return None

    result = row.result if isinstance(row.result, dict) else json.loads(row.result)
    # Mark as cache hit so the caller/frontend can tell
    result["_cache_hit"] = True
    result["_cached_at"] = row.created_at.isoformat() if row.created_at else None
    return result


async def store_analysis_cache(
    session: AsyncSession,
    *,
    user_id: UUID,
    content_hash: str,
    jurisdiction: str,
    mode: str,
    source_file_name: Optional[str],
    result: dict[str, Any],
    ai_model: Optional[str] = None,
    tokens_used: Optional[int] = None,
    processing_time_ms: Optional[int] = None,
) -> None:
    """
    Store an analysis result in the cache.

    Uses INSERT ... ON CONFLICT to upsert: if the same key exists,
    the result is updated (e.g. after a model upgrade).
    """
    expires_at = datetime.now(timezone.utc) + timedelta(days=CACHE_TTL_DAYS)

    # Strip transient fields before caching
    cacheable = {k: v for k, v in result.items() if not k.startswith("_")}

    await session.execute(
        text("""
            INSERT INTO intake_analysis_cache
                (user_id, content_hash, jurisdiction, mode, source_file_name,
                 result, ai_model, tokens_used, processing_time_ms, expires_at)
            VALUES
                (:user_id, :content_hash, :jurisdiction, :mode, :source_file_name,
                 :result::jsonb, :ai_model, :tokens_used, :processing_time_ms, :expires_at)
            ON CONFLICT (user_id, content_hash, jurisdiction, mode)
            DO UPDATE SET
                result = EXCLUDED.result,
                ai_model = EXCLUDED.ai_model,
                tokens_used = EXCLUDED.tokens_used,
                processing_time_ms = EXCLUDED.processing_time_ms,
                source_file_name = EXCLUDED.source_file_name,
                expires_at = EXCLUDED.expires_at,
                created_at = NOW()
        """),
        {
            "user_id": user_id,
            "content_hash": content_hash,
            "jurisdiction": jurisdiction,
            "mode": mode,
            "source_file_name": source_file_name,
            "result": json.dumps(cacheable, ensure_ascii=False, default=str),
            "ai_model": ai_model,
            "tokens_used": tokens_used,
            "processing_time_ms": processing_time_ms,
            "expires_at": expires_at,
        },
    )
    await session.commit()


async def invalidate_user_cache(
    session: AsyncSession,
    *,
    user_id: UUID,
    content_hash: Optional[str] = None,
) -> int:
    """
    Invalidate cache entries for a user.

    If content_hash is provided, only that specific entry is removed.
    Otherwise, all entries for the user are cleared.
    """
    if content_hash:
        result = await session.execute(
            text("""
                DELETE FROM intake_analysis_cache
                WHERE user_id = :user_id AND content_hash = :content_hash
            """),
            {"user_id": user_id, "content_hash": content_hash},
        )
    else:
        result = await session.execute(
            text("DELETE FROM intake_analysis_cache WHERE user_id = :user_id"),
            {"user_id": user_id},
        )
    await session.commit()
    return result.rowcount
