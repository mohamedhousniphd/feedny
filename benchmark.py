import time
import uuid
import sqlite3
import asyncio
import threading
import urllib.request
from unittest.mock import patch, MagicMock
from app.database import import_feedbacks, init_db, get_db
from app.main import analyze_feedbacks_endpoint
from app.models import AnalyzeRequest
from fastapi import Request

# --- Data Import Benchmark ---
def run_import_benchmark():
    init_db()
    # Generate large amount of test data
    test_data = []
    for i in range(1000): # Reduced for quicker benchmark execution by default
        test_data.append({
            'content': f'Test feedback {i}',
            'device_id': str(uuid.uuid4()),
            'created_at': '2023-10-27 10:00:00',
            'included_in_analysis': True,
            'emotion': 1,
            'teacher_id': 1
        })

    # Measure
    start_time = time.time()
    import_feedbacks(test_data)
    end_time = time.time()

    print(f"Time taken for 1000 feedback imports: {end_time - start_time:.4f} seconds")

    # Cleanup
    with get_db() as conn:
        conn.execute("DELETE FROM feedbacks")
        conn.commit()

# --- Analysis Endpoint Benchmark ---
class MockRequest:
    pass

async def mock_analyze_feedbacks(*args, **kwargs):
    await asyncio.sleep(0.1) # Simulate network latency
    return "Mock summary"

def mock_get_feedbacks_by_ids(ids):
    return [{"id": 1, "content": "Great course!", "emotion": 1, "teacher_id": 1} for _ in range(10)]

async def run_analysis_benchmark():
    request_data = AnalyzeRequest(feedback_ids=[1, 2, 3], context="Test")
    req = Request({"type": "http", "scope": {"type": "http", "method": "POST", "path": "/analyze"}})
    teacher = {"id": 1, "is_admin": True, "credits": 10}

    with patch('app.main.get_feedbacks_by_ids_and_teacher', side_effect=mock_get_feedbacks_by_ids):
        with patch('app.main.generate_analysis_content', side_effect=mock_analyze_feedbacks):
            with patch('app.main.save_analysis'):
                start = time.time()
                await analyze_feedbacks_endpoint(request_data, req, teacher)
                duration = time.time() - start
                return duration

# --- Load Testing Benchmark ---
def load_worker(num_requests):
    for _ in range(num_requests):
        try:
            # Note: This requires the server to be running on port 8000
            urllib.request.urlopen("http://localhost:8000/login", timeout=2)
        except Exception:
            pass

def run_load_benchmark(concurrency=10, requests_per_worker=10):
    start = time.time()
    threads = []
    for _ in range(concurrency):
        t = threading.Thread(target=load_worker, args=(requests_per_worker,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    end = time.time()
    total_requests = concurrency * requests_per_worker
    duration = end - start
    print(f"Total load requests (assuming server at :8000): {total_requests}")
    print(f"Time taken: {duration:.4f} seconds")
    if duration > 0:
        print(f"Requests per second: {total_requests / duration:.2f}")

if __name__ == "__main__":
    print("--- Running Import Benchmark ---")
    run_import_benchmark()
    
    print("\n--- Running Analysis Benchmark ---")
    durations = [asyncio.run(run_analysis_benchmark()) for _ in range(3)]
    print(f"Analysis Average Time: {sum(durations)/len(durations):.3f}s")

    print("\n--- Running Load Benchmark (Requires Server at :8000) ---")
    run_load_benchmark(10, 5)
