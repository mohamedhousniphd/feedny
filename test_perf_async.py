import time
import asyncio
from app.main import app
from httpx import AsyncClient, ASGITransport

async def run_async_requests(num_requests):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Define tasks
        tasks = [client.get("/") for _ in range(num_requests)]
        start_time = time.time()
        # Execute concurrently
        responses = await asyncio.gather(*tasks)
        end_time = time.time()

        # Verify
        for r in responses:
            assert r.status_code == 200

        return end_time - start_time

if __name__ == "__main__":
    duration = asyncio.run(run_async_requests(500))
    print(f"500 concurrent requests took {duration:.4f} seconds ({(500/duration):.2f} req/s)")
