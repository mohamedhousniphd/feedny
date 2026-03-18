import time
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def benchmark():
    # Warmup
    client.get("/login")

    start = time.time()
    for _ in range(1000):
        client.get("/login")
    end = time.time()
    print(f"Time for 1000 requests to /login: {end - start:.4f} seconds")

if __name__ == "__main__":
    benchmark()
