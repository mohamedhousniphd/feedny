import time
import os
import asyncio

template_cache = {}

async def get_template(path: str) -> str:
    if path not in template_cache:
        def read_file():
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        template_cache[path] = await asyncio.to_thread(read_file)
    return template_cache[path]

async def benchmark_cache():
    # Warmup
    await get_template("app/static/login.html")

    start = time.time()
    for _ in range(10000):
        _ = await get_template("app/static/login.html")
    end = time.time()
    print(f"Time for 10000 cached reads: {end - start:.4f} seconds")

if __name__ == "__main__":
    asyncio.run(benchmark_cache())
