"""Shared pytest fixtures."""

import copy
import sqlite3

import pytest

from anthropic_tracker.db import init_db

from .fixtures import SAMPLE_JOBS


@pytest.fixture
def db():
    """In-memory SQLite database with schema applied."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    init_db(conn)
    yield conn
    conn.close()


@pytest.fixture
def sample_jobs():
    """Return a copy of the sample jobs list."""
    return copy.deepcopy(SAMPLE_JOBS)
