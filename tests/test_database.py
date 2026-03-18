import pytest
import os
import app.database
from app.database import init_db, check_device_limit, increment_device_feedback

@pytest.fixture(autouse=True)
def test_db(tmp_path):
    """Set up a temporary database for testing."""
    # Override the database URL to use a temporary file
    db_file = tmp_path / "test_feedny.db"
    original_url = app.database.DATABASE_URL
    app.database.DATABASE_URL = str(db_file)

    # Initialize the database schema
    init_db()

    yield

    # Cleanup: restore the original URL
    app.database.DATABASE_URL = original_url

    # Optional cleanup of the file, though tmp_path handles its own cleanup
    if db_file.exists():
        os.remove(db_file)

def test_check_device_limit_new_device():
    """Test that a new device can submit and has 0 feedback count."""
    can_submit, count = check_device_limit("device_1")
    assert can_submit is True
    assert count == 0

def test_check_device_limit_after_increment():
    """Test that a device cannot submit after its feedback count is incremented."""
    device_id = "device_1"

    # Increment feedback count
    increment_device_feedback(device_id)

    # Check limit again
    can_submit, count = check_device_limit(device_id)
    assert can_submit is False
    assert count == 1

    # Increment again to see if it updates
    increment_device_feedback(device_id)
    can_submit, count = check_device_limit(device_id)
    assert can_submit is False
    assert count == 2

def test_check_device_limit_multiple_devices():
    """Test that limits are tracked separately for different devices."""
    device_1 = "device_1"
    device_2 = "device_2"

    # Increment device 1
    increment_device_feedback(device_1)

    # Device 1 should not be able to submit
    can_submit_1, count_1 = check_device_limit(device_1)
    assert can_submit_1 is False
    assert count_1 == 1

    # Device 2 should still be able to submit
    can_submit_2, count_2 = check_device_limit(device_2)
    assert can_submit_2 is True
    assert count_2 == 0
