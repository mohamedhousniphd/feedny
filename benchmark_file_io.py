import time
import os

def load_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def benchmark_disk():
    start = time.time()
    for _ in range(10000):
        _ = load_file("app/static/login.html")
    end = time.time()
    print(f"Time for 10000 reads: {end - start:.4f} seconds")

if __name__ == "__main__":
    benchmark_disk()
