<<<<<<< HEAD
import time
import uuid
import sqlite3
import asyncio
from unittest.mock import patch, MagicMock
from app.database import import_feedbacks, init_db, get_db
from app.main import analyze_feedbacks_endpoint
from app.models import AnalyzeRequest
from fastapi import Request

# Import performance benchmark
def run_import_benchmark():
    init_db()
    # Generate large amount of test data
    test_data = []
    for i in range(100000):
        test_data.append({
            'content': f'Test feedback {i}',
            'device_id': str(uuid.uuid4()),
            'created_at': '2023-10-27 10:00:00',
            'included_in_analysis': True,
            'emotion': 'happy',
            'teacher_id': 1
        })

    # Measure
    start_time = time.time()
    import_feedbacks(test_data)
    end_time = time.time()

    print(f"Time taken for 100000 feedback imports: {end_time - start_time:.4f} seconds")

    # Cleanup
    with get_db() as conn:
        conn.execute("DELETE FROM feedbacks")
        conn.commit()

# Analysis performance benchmark
class MockRequest:
    pass

async def mock_analyze_feedbacks(*args, **kwargs):
    await asyncio.sleep(1.0) # Simulate 1s network latency
    return "Mock summary"

def mock_get_feedbacks_by_ids(ids):
    return [{"id": 1, "content": "Great course!", "emotion": "happy", "teacher_id": 1} for _ in range(10)]

async def run_analysis_benchmark():
    request_data = AnalyzeRequest(feedback_ids=[1, 2, 3], context="Test")
    req = Request({"type": "http"})
    teacher = {"id": 1, "is_admin": True, "credits": 10}

    with patch('app.main.get_feedbacks_by_ids', side_effect=mock_get_feedbacks_by_ids):
        with patch('app.main.analyze_feedbacks', side_effect=mock_analyze_feedbacks):
            with patch('app.main.save_analysis'):
                start = time.time()
                await analyze_feedbacks_endpoint(request_data, req, teacher)
                duration = time.time() - start
                return duration

if __name__ == "__main__":
    print("--- Running Import Benchmark ---")
    run_import_benchmark()
    
    print("\n--- Running Analysis Benchmark ---")
    durations = [asyncio.run(run_analysis_benchmark()) for _ in range(3)]
    print(f"Analysis Average Time: {sum(durations)/len(durations):.3f}s")
=======
import urllib.request
import time
import threading

def worker(num_requests):
    for _ in range(num_requests):
        try:
            urllib.request.urlopen("http://localhost:8000/login", timeout=2)
        except Exception:
            pass

def run_benchmark(concurrency=10, requests_per_worker=100):
    start = time.time()
    threads = []
    for _ in range(concurrency):
        t = threading.Thread(target=worker, args=(requests_per_worker,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    end = time.time()
    total_requests = concurrency * requests_per_worker
    duration = end - start
    print(f"Total requests: {total_requests}")
    print(f"Time taken: {duration:.4f} seconds")
    print(f"Requests per second: {total_requests / duration:.2f}")

if __name__ == "__main__":
    run_benchmark(50, 100)
>>>>>>> origin/jules/optimize-file-io-async-routes-13981045764482344947
