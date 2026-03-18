import os
import tempfile
import pytest
from app import database

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    fd, path = tempfile.mkstemp()
    os.close(fd)
    monkeypatch.setattr(database, "DATABASE_URL", path)
    database.init_db()
    yield
    os.remove(path)

def test_get_feedbacks_by_ids_empty():
    result = database.get_feedbacks_by_ids([])
    assert result == []

def test_get_feedbacks_by_ids_none():
    result = database.get_feedbacks_by_ids(None)
    assert result == []

def test_get_feedbacks_by_ids_multiple():
    # Insert some feedbacks
    id1 = database.insert_feedback("Feedback 1", "device_1", emotion=1, teacher_id=1)
    id2 = database.insert_feedback("Feedback 2", "device_2", emotion=2, teacher_id=1)
    id3 = database.insert_feedback("Feedback 3", "device_3", emotion=3, teacher_id=1)

    result = database.get_feedbacks_by_ids([id1, id3])
    assert len(result) == 2

    # Sort results by ID to ensure consistent checking
    result.sort(key=lambda x: x["id"])

    assert result[0]["id"] == id1
    assert result[0]["content"] == "Feedback 1"
    assert result[0]["device_id"] == "device_1"

    assert result[1]["id"] == id3
    assert result[1]["content"] == "Feedback 3"
    assert result[1]["device_id"] == "device_3"

def test_get_feedbacks_by_ids_invalid_id():
    # Insert one feedback
    id1 = database.insert_feedback("Feedback 1", "device_1", emotion=1, teacher_id=1)

    # Request an ID that doesn't exist along with one that does
    result = database.get_feedbacks_by_ids([id1, 9999])

    assert len(result) == 1
    assert result[0]["id"] == id1
