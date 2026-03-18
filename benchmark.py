import time
import asyncio
from unittest.mock import patch, MagicMock
from app.main import analyze_feedbacks_endpoint
from app.models import AnalyzeRequest
from fastapi import Request

class MockRequest:
    pass

async def mock_analyze_feedbacks(*args, **kwargs):
    await asyncio.sleep(1.0) # Simulate 1s network latency
    return "Mock summary"

def mock_get_feedbacks_by_ids(ids):
    return [{"id": 1, "content": "Great course!", "emotion": "happy", "teacher_id": 1} for _ in range(10)]

async def run_benchmark():
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
    durations = [asyncio.run(run_benchmark()) for _ in range(3)]
    print(f"Baseline Time: {sum(durations)/len(durations):.3f}s")
