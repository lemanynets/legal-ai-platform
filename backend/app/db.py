"""
Database connection and session management.
Async SQLAlchemy engine backed by PostgreSQL (asyncpg).
"""
from __future__ import annotations

import os
import re
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


_DEFAULT_URL = "postgresql+asyncpg://legal_ai:secret@db:5432/legal_ai"


def _build_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip() or _DEFAULT_URL
    # Normalise scheme: postgres:// → postgresql+asyncpg://
    url = url.replace("postgres://", "postgresql://", 1)
    url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    # asyncpg doesn't understand ?sslmode= — strip it; we handle SSL via connect_args
    url = re.sub(r"[?&]sslmode=[^&]*", "", url)
    url = re.sub(r"\?$", "", url)
    return url


DATABASE_URL = _build_database_url()

# Enable SSL when the env var DB_SSL=true is set (Railway external connections)
_raw = os.environ.get("DATABASE_URL", "")
_ssl: bool | str = False
if os.environ.get("DB_SSL", "").lower() == "true":
    _ssl = "require"
elif "sslmode=require" in _raw or "sslmode=verify" in _raw:
    _ssl = "require"

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args={"ssl": _ssl} if _ssl else {},
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
