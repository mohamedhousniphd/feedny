import pytest
import sqlite3
import os
from app import database
from datetime import datetime

@pytest.fixture(autouse=True)
def test_db(tmp_path, monkeypatch):
    """
    Fixture to create a temporary database for each test.
    Automatically used by all tests in this module.
    """
    db_file = tmp_path / "test_feedny.db"
    monkeypatch.setattr(database, "DATABASE_URL", str(db_file))

    # Initialize the database
    database.init_db()

    yield str(db_file)

    # Cleanup is handled by tmp_path

def test_init_db(test_db):
    """Test that the database initializes correctly with all tables."""
    # init_db is already called in the fixture, so we just verify tables exist
    with database.get_db() as conn:
        tables = [
            "feedbacks", "device_limits", "settings", "teachers",
            "payment_receipts", "analysis_history"
        ]
        for table in tables:
            cursor = conn.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            assert cursor.fetchone() is not None

def test_insert_and_get_feedback():
    """Test inserting and retrieving feedback."""
    # Default teacher_id is 1
    feedback_id = database.insert_feedback(
        content="Great class!",
        device_id="device123",
        emotion=1,
        teacher_id=1
    )
    assert feedback_id is not None
    assert feedback_id > 0

    # Test get_feedback_by_id
    feedback = database.get_feedback_by_id(feedback_id)
    assert feedback is not None
    assert feedback["content"] == "Great class!"
    assert feedback["device_id"] == "device123"
    assert feedback["emotion"] == 1
    assert feedback["teacher_id"] == 1
    assert feedback["included_in_analysis"] == 0

    # Test get_all_feedbacks
    feedbacks = database.get_all_feedbacks(teacher_id=1)
    assert len(feedbacks) == 1
    assert feedbacks[0]["id"] == feedback_id

    # Test get_all_feedbacks for different teacher
    feedbacks_empty = database.get_all_feedbacks(teacher_id=2)
    assert len(feedbacks_empty) == 0

def test_toggle_feedback_inclusion():
    """Test toggling the included_in_analysis status."""
    feedback_id = database.insert_feedback("Test", "dev1", teacher_id=1)

    # Initially 0
    fb = database.get_feedback_by_id(feedback_id)
    assert fb["included_in_analysis"] == 0

    # Toggle to 1
    success = database.toggle_feedback_inclusion(feedback_id)
    assert success is True
    fb = database.get_feedback_by_id(feedback_id)
    assert fb["included_in_analysis"] == 1

    # Toggle back to 0
    success = database.toggle_feedback_inclusion(feedback_id)
    assert success is True
    fb = database.get_feedback_by_id(feedback_id)
    assert fb["included_in_analysis"] == 0

def test_get_feedbacks_by_ids():
    """Test getting multiple feedbacks by their IDs."""
    id1 = database.insert_feedback("F1", "dev1", teacher_id=1)
    id2 = database.insert_feedback("F2", "dev2", teacher_id=1)

    feedbacks = database.get_feedbacks_by_ids([id1, id2])
    assert len(feedbacks) == 2
    ids = [fb["id"] for fb in feedbacks]
    assert id1 in ids
    assert id2 in ids

    # Empty list
    assert database.get_feedbacks_by_ids([]) == []

def test_device_limits():
    """Test device limit checking and incrementing."""
    # Initial state
    can_submit, count = database.check_device_limit("dev1")
    assert can_submit is True
    assert count == 0

    # Increment
    database.increment_device_feedback("dev1")
    can_submit, count = database.check_device_limit("dev1")
    assert can_submit is False
    assert count == 1

    # Increment again
    database.increment_device_feedback("dev1")
    can_submit, count = database.check_device_limit("dev1")
    assert can_submit is False
    assert count == 2

def test_reset_database():
    """Test resetting feedbacks and device limits."""
    database.insert_feedback("Test", "dev1", teacher_id=1)
    database.increment_device_feedback("dev1")

    database.reset_database()

    # Verify feedbacks empty
    assert len(database.get_all_feedbacks(teacher_id=1)) == 0

    # Verify device limits empty
    can_submit, count = database.check_device_limit("dev1")
    assert can_submit is True
    assert count == 0

def test_get_feedback_stats():
    """Test feedback statistics calculation."""
    id1 = database.insert_feedback("F1", "dev1", teacher_id=1)
    id2 = database.insert_feedback("F2", "dev2", teacher_id=1)
    id3 = database.insert_feedback("F3", "dev3", teacher_id=2)

    database.toggle_feedback_inclusion(id1)

    stats1 = database.get_feedback_stats(teacher_id=1)
    assert stats1["total"] == 2
    assert stats1["selected"] == 1

    stats2 = database.get_feedback_stats(teacher_id=2)
    assert stats2["total"] == 1
    assert stats2["selected"] == 0

def test_import_feedbacks():
    """Test importing feedbacks from data."""
    data = [
        {"content": "A", "device_id": "d1", "emotion": 1, "included_in_analysis": True, "teacher_id": 1, "created_at": "2023-01-01 10:00:00"},
        {"content": "B", "included_in_analysis": False, "teacher_id": 2} # Missing optional fields
    ]

    imported = database.import_feedbacks(data)
    assert imported == 2

    fb1 = database.get_all_feedbacks(teacher_id=1)
    assert len(fb1) == 1
    assert fb1[0]["content"] == "A"
    assert fb1[0]["emotion"] == 1
    assert fb1[0]["included_in_analysis"] == 1
    assert fb1[0]["created_at"] == "2023-01-01 10:00:00"

    fb2 = database.get_all_feedbacks(teacher_id=2)
    assert len(fb2) == 1
    assert fb2[0]["content"] == "B"
    assert fb2[0]["included_in_analysis"] == 0

    # Empty import
    assert database.import_feedbacks([]) == 0

def test_settings():
    """Test setting and getting key-value pairs."""
    # Default value
    assert database.get_setting("theme", "light") == "light"

    # Set and get
    database.set_setting("theme", "dark")
    assert database.get_setting("theme") == "dark"

    # Update existing
    database.set_setting("theme", "blue")
    assert database.get_setting("theme") == "blue"

def test_teacher_management():
    """Test creating and managing teachers."""
    # Create teacher
    teacher_id = database.create_teacher("John", "john@test.com", "hash1", "CODE1")
    assert teacher_id is not None

    # Duplicate email should fail
    assert database.create_teacher("Jane", "john@test.com", "hash2", "CODE2") is None

    # Duplicate code should fail
    assert database.create_teacher("Jane", "jane@test.com", "hash2", "CODE1") is None

    # Get teacher
    teacher = database.get_teacher_by_email("john@test.com")
    assert teacher["name"] == "John"
    assert teacher["unique_code"] == "CODE1"

    teacher_by_id = database.get_teacher_by_id(teacher_id)
    assert teacher_by_id["email"] == "john@test.com"

    teacher_by_code = database.get_teacher_by_code("CODE1")
    assert teacher_by_code["email"] == "john@test.com"

    # Update password
    assert database.update_teacher_password("john@test.com", "new_hash") is True
    teacher = database.get_teacher_by_email("john@test.com")
    assert teacher["password_hash"] == "new_hash"

    # Update password for non-existent
    assert database.update_teacher_password("nobody@test.com", "hash") is False

    # Update code
    assert database.update_teacher_code(teacher_id, "NEWCODE") is True
    teacher = database.get_teacher_by_id(teacher_id)
    assert teacher["unique_code"] == "NEWCODE"

    # Update code to duplicate
    t2_id = database.create_teacher("T2", "t2@test.com", "h", "C2")
    assert database.update_teacher_code(t2_id, "NEWCODE") is False

    # Credits
    assert teacher["credits"] == 3 # Default
    assert database.deduct_credit(teacher_id) is True
    t_after_deduct = database.get_teacher_by_id(teacher_id)
    assert t_after_deduct["credits"] == 2

    database.add_credits(teacher_id, 5)
    t_after_add = database.get_teacher_by_id(teacher_id)
    assert t_after_add["credits"] == 7

    # Get all teachers
    teachers = database.get_all_teachers()
    assert len(teachers) == 2

def test_payment_receipts():
    """Test payment receipt management."""
    t_id = database.create_teacher("T1", "t1@test.com", "h", "C1")

    # Create receipt
    r_id = database.create_payment_receipt(t_id, "/path/to/file")
    assert r_id is not None

    # Get receipt
    r = database.get_receipt_by_id(r_id)
    assert r["teacher_id"] == t_id
    assert r["file_path"] == "/path/to/file"
    assert r["status"] == "pending"

    # Update status
    assert database.update_receipt_status(r_id, "approved") is True
    r = database.get_receipt_by_id(r_id)
    assert r["status"] == "approved"

    # Get all receipts
    receipts = database.get_all_receipts()
    assert len(receipts) == 1
    assert receipts[0]["teacher_name"] == "T1"
    assert receipts[0]["teacher_email"] == "t1@test.com"

def test_analysis_history():
    """Test saving and retrieving analysis history."""
    t_id = database.create_teacher("T1", "t1@test.com", "h", "C1")

    # Save analysis
    a_id = database.save_analysis(t_id, "Summary", "img.png", 10, "Context")
    assert a_id is not None

    # Get history
    history = database.get_analysis_history(t_id)
    assert len(history) == 1
    assert history[0]["summary"] == "Summary"
    assert history[0]["wordcloud_image"] == "img.png"
    assert history[0]["feedback_count"] == 10
    assert history[0]["context"] == "Context"

    # Delete analysis - success
    assert database.delete_analysis_by_id(a_id, t_id) is True
    assert len(database.get_analysis_history(t_id)) == 0

    # Delete analysis - non-existent or wrong teacher
    a_id2 = database.save_analysis(t_id, "S2", "i2.png", 5, "C2")
    assert database.delete_analysis_by_id(a_id2, 999) is False
