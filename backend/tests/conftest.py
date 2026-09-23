"""Pytest fixtures.

Tests run against an in-memory SQLite database so they don't depend on
Postgres or PostGIS. Geometry columns store GeoJSON dicts, which works
identically on both backends.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from tempfile import TemporaryDirectory

# Configure environment before anything else imports settings.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AQUALENS_USE_SAMPLE_PROVIDER", "1")
os.environ.setdefault("AQUALENS_FAKE_GEMINI", "1")
# Default the test suite to the deterministic single-call reasoning
# path so the existing tests stay meaningful. Agent-specific tests opt
# in to the multi-agent flow per-test.
os.environ.setdefault("AQUALENS_AGENTIC_MODE", "0")
os.environ.setdefault("GOOGLE_API_KEY", "test-key")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlmodel import Session, SQLModel

from app.core import config as config_module
from app.core.database import get_engine
from app.main import create_app


@pytest.fixture(scope="session", autouse=True)
def _settings_isolation() -> Iterator[None]:
    """Pin upload/report dirs to a temp directory shared across the test session."""
    with TemporaryDirectory() as tmp:
        config_module.get_settings.cache_clear()
        os.environ["UPLOAD_DIR"] = str(Path(tmp) / "uploads")
        os.environ["REPORT_DIR"] = str(Path(tmp) / "reports")
        yield


@pytest.fixture()
def db_engine():
    """Recreate the schema before each test for full isolation."""
    config_module.get_settings.cache_clear()
    # Reset cached engine in case prior tests cached a different URL.
    from app.core import database as database_module

    database_module.get_engine.cache_clear()

    engine = get_engine()
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    # Enable foreign keys for SQLite.
    @event.listens_for(engine, "connect")
    def _fk_pragma(dbapi_connection, _connection_record):  # pragma: no cover
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture()
def db_session(db_engine) -> Iterator[Session]:
    """Plain SQLModel ``Session`` for tests that talk to the DB directly."""
    with Session(db_engine) as session:
        yield session


@pytest.fixture()
def client(db_engine) -> Iterator[TestClient]:
    """FastAPI test client with the schema initialised."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def sample_polygon() -> dict[str, object]:
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [9.20, 45.95],
                [9.30, 45.95],
                [9.30, 46.02],
                [9.20, 46.02],
                [9.20, 45.95],
            ]
        ],
    }
