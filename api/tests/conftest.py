"""Pytest fixtures for PgSessionStorage tests."""

import os

import psycopg
import pytest

from app.storage.pg_session_storage import PgSessionStorage


@pytest.fixture(scope="session")
def pg_url():
    """Database URL — reads DATABASE_URL or falls back to local default."""
    return os.getenv("DATABASE_URL", "postgresql://localhost/orbital")


@pytest.fixture()
def storage(pg_url):
    """
    Yield a PgSessionStorage wired to a real PostgreSQL database.

    Drops both tables after each test to guarantee isolation.
    """
    store = PgSessionStorage(pg_url)
    store.initialize()
    yield store

    # Teardown: drop test tables so each test starts fresh
    try:
        with store.conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS artifacts")
            cur.execute("DROP TABLE IF EXISTS sessions")
        store.conn.commit()
    finally:
        store.close()
