"""
FastAPI router for user preferences (smart defaults).

GET  /api/users/me/preferences  — retrieve current preferences
PATCH /api/users/me/preferences — merge-update preferences
"""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter()


class UserPreferencesSchema(BaseModel):
    gen_mode: Optional[str] = None
    gen_style: Optional[str] = None
    target_language: Optional[str] = None
    include_digest: Optional[bool] = None
    default_doc_type: Optional[str] = None
    case_law_only_supreme: Optional[bool] = None
    case_law_court_type: Optional[str] = None
    case_law_source: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers — use a dedicated `user_preferences` table with a JSONB column.
# Falls back gracefully if the table does not exist yet.
# ---------------------------------------------------------------------------

_CREATE_TABLE_SQL = text("""
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id TEXT PRIMARY KEY,
    prefs   JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
""")

_UPSERT_SQL = text("""
INSERT INTO user_preferences (user_id, prefs, updated_at)
VALUES (:user_id, :prefs::jsonb, now())
ON CONFLICT (user_id) DO UPDATE
SET prefs = user_preferences.prefs || :prefs::jsonb,
    updated_at = now()
RETURNING prefs;
""")

_SELECT_SQL = text("""
SELECT prefs FROM user_preferences WHERE user_id = :user_id;
""")


async def _ensure_table(session: AsyncSession) -> None:
    """Idempotently create the preferences table."""
    await session.execute(_CREATE_TABLE_SQL)
    await session.commit()


@router.get("/me/preferences", response_model=UserPreferencesSchema)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserPreferencesSchema:
    await _ensure_table(session)
    result = await session.execute(_SELECT_SQL, {"user_id": current_user.id})
    row = result.first()
    if row is None:
        return UserPreferencesSchema()
    return UserPreferencesSchema(**row[0])


@router.patch("/me/preferences", response_model=UserPreferencesSchema)
async def update_preferences(
    payload: UserPreferencesSchema,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserPreferencesSchema:
    import json

    await _ensure_table(session)
    # Only include non-None fields so we don't clobber unrelated prefs
    update_data = payload.model_dump(exclude_none=True)
    if not update_data:
        # Nothing to update — return current prefs
        return await get_preferences(current_user, session)

    result = await session.execute(
        _UPSERT_SQL,
        {"user_id": current_user.id, "prefs": json.dumps(update_data)},
    )
    await session.commit()
    row = result.first()
    return UserPreferencesSchema(**row[0]) if row else UserPreferencesSchema(**update_data)
