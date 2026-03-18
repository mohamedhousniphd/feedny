import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

def blocking_sync_task(duration: float):
    time.sleep(duration)
    return "Result"

async def background_poller():
    ticks = 0
    start = time.perf_counter()
    while ticks < 10:
        await asyncio.sleep(0.1)
        ticks += 1
        print(f"  Poller tick {ticks} at {time.perf_counter() - start:.2f}s")

async def run_in_threadpool(executor, func, *args):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, func, *args)

async def main():
    print("\nScenario 1: Blocking call in async function")
    poller = asyncio.create_task(background_poller())
    # The poller won't start until we yield the event loop
    await asyncio.sleep(0.01)

    print("  Handler: starting blocking task (1.0s)...")
    start = time.perf_counter()
    blocking_sync_task(1.0)
    print(f"  Handler: finished blocking task in {time.perf_counter() - start:.2f}s")

    await poller
    print(f"Total time (Scenario 1): {time.perf_counter() - start:.4f}s")

    print("\nScenario 2: Offloading blocking call to threadpool")
    executor = ThreadPoolExecutor()
    poller = asyncio.create_task(background_poller())
    await asyncio.sleep(0.01)

    print("  Handler: starting offloaded task (1.0s)...")
    start = time.perf_counter()
    await run_in_threadpool(executor, blocking_sync_task, 1.0)
    print(f"  Handler: finished offloaded task in {time.perf_counter() - start:.2f}s")

    await poller
    print(f"Total time (Scenario 2): {time.perf_counter() - start:.4f}s")
    executor.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
