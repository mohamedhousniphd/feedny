import os
import io
from fastapi.testclient import TestClient
from app.main import app, get_current_teacher
from app.database import init_db, create_teacher, get_teacher_by_email

# Set up test database or ensure tables exist
def setup_test_db():
    init_db()
    teacher = get_teacher_by_email("test_upload@example.com")
    if not teacher:
        create_teacher("Test Upload", "test_upload@example.com", "dummy_hash", "TUP123")
    return get_teacher_by_email("test_upload@example.com")

def override_get_current_teacher():
    teacher = setup_test_db()
    if teacher:
        return teacher
    return {"id": 1, "email": "test@example.com", "name": "Test Teacher"}

app.dependency_overrides[get_current_teacher] = override_get_current_teacher

client = TestClient(app)

def test_upload_allowed_extension():
    # Test uploading a .pdf file
    file_content = b"Dummy PDF content"
    files = {"file": ("test_receipt.pdf", io.BytesIO(file_content), "application/pdf")}

    response = client.post("/api/payment/upload", files=files)

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    print("Allowed extension test passed!")

def test_upload_disallowed_extension():
    # Test uploading a .txt file
    file_content = b"Dummy TXT content"
    files = {"file": ("test_receipt.txt", io.BytesIO(file_content), "text/plain")}

    response = client.post("/api/payment/upload", files=files)

    assert response.status_code == 400
    assert "Format de fichier non autorisé" in response.json()["detail"]
    print("Disallowed extension test passed!")

if __name__ == "__main__":
    test_upload_allowed_extension()
    test_upload_disallowed_extension()
    print("All tests passed!")
