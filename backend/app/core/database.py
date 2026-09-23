"""SQLAlchemy engine, session factory, and FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

from app.core.config import get_settings


def _normalise_database_url(url: str) -> str:
    """Coerce common managed-Postgres URL shapes to a SQLAlchemy-friendly form.

    Supabase / Neon / RDS hand out URLs that start with ``postgresql://``
    or ``postgres://``. SQLAlchemy uses these to pick a driver via dialect
    name, and we pin it to ``psycopg`` (psycopg 3) which is what our
    ``requirements.txt`` installs. Without this normalisation, the engine
    falls back to ``psycopg2`` which isn't in the image.
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and "+" not in url.split("://", 1)[0]:
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Return the singleton SQLAlchemy engine."""
    settings = get_settings()
    url = _normalise_database_url(settings.database_url)
    connect_args: dict[str, object] = {}
    engine_kwargs: dict[str, object] = {
        "echo": False,
        "future": True,
        "pool_pre_ping": True,
    }
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        # ``sqlite:///:memory:`` creates a fresh DB per connection by
        # default. API tests open multiple connections/threads, so use
        # StaticPool to keep one shared in-memory DB.
        if ":memory:" in url:
            engine_kwargs["poolclass"] = StaticPool
    return create_engine(url, connect_args=connect_args, **engine_kwargs)


def create_all() -> None:
    """Create tables from the SQLModel metadata.

    Used by tests and the SQLite development path; production migrations
    go through Alembic.
    """
    # Import models so their metadata is registered before create_all.
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(get_engine())


def get_session() -> Generator[Session]:
    """FastAPI dependency that yields a database session."""
    with Session(get_engine()) as session:
        yield session
