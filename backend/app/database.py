from __future__ import annotations

import logging
from typing import Generator
from urllib.parse import urlparse, urlunparse

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)


def _mask_db_url(url: str) -> str:
    """Маскує пароль у URL бази даних для безпечного логування."""
    try:
        parsed = urlparse(url)
        if parsed.password:
            masked_netloc = f"{parsed.username}:***@{parsed.hostname}:{parsed.port}"
            masked = parsed._replace(netloc=masked_netloc)
            return urlunparse(masked)
    except Exception:
        pass
    return url


db_url = settings.database_url
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

logger.info("Database connection initialized: %s", _mask_db_url(db_url))

engine_kwargs = {
    "future": True,
}
if db_url.startswith("postgresql+"):
    engine_kwargs.update(
        {
            "pool_pre_ping": True,
            "pool_size": 20,
            "max_overflow": 10,
            "pool_timeout": 30,
            "pool_recycle": 1800,
        }
    )

engine = create_engine(db_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
