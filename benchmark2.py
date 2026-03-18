import time
import os

def read_file_sync():
    with open("app/static/index.html", "r", encoding="utf-8") as f:
        html = f.read()
    return html

# We will implement caching and benchmark the difference
cache = {}

def read_file_cached():
    path = "app/static/index.html"
    if path not in cache:
        with open(path, "r", encoding="utf-8") as f:
            cache[path] = f.read()
    return cache[path]

iterations = 50000

start_time = time.time()
for _ in range(iterations):
    read_file_sync()
sync_time = time.time() - start_time

start_time = time.time()
for _ in range(iterations):
    read_file_cached()
cached_time = time.time() - start_time

print(f"Sync time: {sync_time:.4f} seconds")
print(f"Cached time: {cached_time:.4f} seconds")
print(f"Speedup: {sync_time / cached_time:.2f}x")
