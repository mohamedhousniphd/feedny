import pytest
import sqlite3
import os

from app.database import increment_device_feedback, get_db, init_db, check_device_limit

# Mocking database path for testing
def test_increment_device_feedback(monkeypatch, tmp_path):
    test_db_path = tmp_path / "test_feedny.db"

    monkeypatch.setattr("app.database.DATABASE_URL", str(test_db_path))

    # Initialize the test database
    init_db()

    device_id = "test_device_123"

    # Check initial state
    can_submit, count = check_device_limit(device_id)
    assert can_submit is True
    assert count == 0

    # Increment once
    increment_device_feedback(device_id)

    can_submit, count = check_device_limit(device_id)
    assert can_submit is False
    assert count == 1

    # Increment twice
    increment_device_feedback(device_id)

    can_submit, count = check_device_limit(device_id)
    assert can_submit is False
    assert count == 2
