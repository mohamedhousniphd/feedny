import asyncio
import time
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import init_db, insert_feedback, create_teacher, get_teacher_by_email
from app.main import export_csv
from fastapi import Request
from unittest.mock import MagicMock

def setup_db():
    if os.path.exists("./data/feedny.db"):
        os.remove("./data/feedny.db")
    init_db()
    # Create teacher
    create_teacher("Bench Teacher", "bench@test.com", "hash", "CODE")
    teacher = get_teacher_by_email("bench@test.com")

    # Insert a lot of feedbacks
    for i in range(1000):
        insert_feedback(f"Test feedback {i}", f"device_{i}", "happy", teacher['id'])
    return teacher

async def run_benchmark():
    teacher = setup_db()

    request_mock = MagicMock()

    start_time = time.time()
    # Assuming the current implementation signature is `export_csv(request, teacher)`
    try:
        # Check current implementation
        response = await export_csv(request_mock, teacher)
        # Check the size to ensure it did something
        # print(f"CSV size: {len(response.body)}")
    except Exception as e:
        print(f"Error: {e}")

    end_time = time.time()
    print(f"Baseline Time: {end_time - start_time:.4f} seconds")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
