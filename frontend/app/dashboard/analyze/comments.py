"""
FastAPI router for collaborative analysis comments.

Endpoints:
  GET    /api/analyze/{intake_id}/comments               list comments
  POST   /api/analyze/{intake_id}/comments               add comment
  DELETE /api/analyze/{intake_id}/comments/{comment_id}  delete own comment
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter()

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class CommentOut(BaseModel):
    id: str
    intake_id: str
    user_id: str
    user_name: str | None
    content: str
    created_at: str


# ---------------------------------------------------------------------------
# Table bootstrap (idempotent)
# ---------------------------------------------------------------------------

_CREATE_TABLE = text("""
CREATE TABLE IF NOT EXISTS analysis_comments (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intake_id   UUID NOT NULL,
    user_id     UUID NOT NULL,
    user_name   TEXT,
    content     TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_analysis_comments_intake
    ON analysis_comments (intake_id, created_at);
""")


async def _ensure_table(session: AsyncSession) -> None:
    await session.execute(_CREATE_TABLE)
    await session.commit()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/{intake_id}/comments",
    response_model=list[CommentOut],
    summary="List comments for an analysis",
)
async def list_comments(
    intake_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[CommentOut]:
    await _ensure_table(session)
    result = await session.execute(
        text("""
            SELECT id::text, intake_id::text, user_id::text,
                   user_name, content, created_at::text
            FROM analysis_comments
            WHERE intake_id = :intake_id
            ORDER BY created_at ASC
        """),
        {"intake_id": str(intake_id)},
    )
    rows = result.fetchall()
    return [
        CommentOut(
            id=row[0],
            intake_id=row[1],
            user_id=row[2],
            user_name=row[3],
            content=row[4],
            created_at=row[5],
        )
        for row in rows
    ]


@router.post(
    "/{intake_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment to an analysis",
)
async def create_comment(
    intake_id: UUID,
    payload: CommentCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CommentOut:
    await _ensure_table(session)
    result = await session.execute(
        text("""
            INSERT INTO analysis_comments (intake_id, user_id, user_name, content)
            VALUES (:intake_id, :user_id, :user_name, :content)
            RETURNING id::text, intake_id::text, user_id::text,
                      user_name, content, created_at::text
        """),
        {
            "intake_id": str(intake_id),
            "user_id": str(current_user.id),
            "user_name": getattr(current_user, "full_name", None)
                         or getattr(current_user, "email", None),
            "content": payload.content,
        },
    )
    await session.commit()
    row = result.fetchone()
    return CommentOut(
        id=row[0],
        intake_id=row[1],
        user_id=row[2],
        user_name=row[3],
        content=row[4],
        created_at=row[5],
    )


@router.delete(
    "/{intake_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete own comment",
)
async def delete_comment(
    intake_id: UUID,
    comment_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    await _ensure_table(session)
    result = await session.execute(
        text("""
            DELETE FROM analysis_comments
            WHERE id = :comment_id
              AND intake_id = :intake_id
              AND user_id = :user_id
        """),
        {
            "comment_id": str(comment_id),
            "intake_id": str(intake_id),
            "user_id": str(current_user.id),
        },
    )
    await session.commit()
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found or not owned by current user.",
        )
