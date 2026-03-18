import time
import asyncio
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_student_page_sync():
    start_time = time.time()
    for _ in range(500):
        response = client.get("/")
        assert response.status_code == 200
    end_time = time.time()
    return end_time - start_time

if __name__ == "__main__":
    duration = test_student_page_sync()
    print(f"500 requests took {duration:.4f} seconds ({(500/duration):.2f} req/s)")
