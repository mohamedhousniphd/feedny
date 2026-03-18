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
