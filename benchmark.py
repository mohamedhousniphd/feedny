import time
from app.main import student_page

import asyncio
from unittest.mock import MagicMock

async def run_benchmark():
    request = MagicMock()
    request.cookies.get.return_value = "TEST_CODE"

    # Mock database functions so they don't hit the DB or so they return quickly
    import app.main as main
    main.get_teacher_by_code = lambda c: {'id': 1, 'name': 'Test Teacher', 'unique_code': 'TEST_CODE'}
    main.get_device_id = lambda r: 'test_device'
    main.check_device_limit = lambda d: (True, 0)
    main.get_setting = lambda k, d: 'Comment s\'est passé votre cours ?'

    iterations = 1000
    start_time = time.time()

    for _ in range(iterations):
        await student_page(request, code="TEST_CODE")

    end_time = time.time()
    print(f"Time taken for {iterations} iterations: {end_time - start_time:.4f} seconds")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
