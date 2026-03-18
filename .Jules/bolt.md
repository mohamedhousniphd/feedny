# Performance Optimization: Template Caching
- **Bottleneck**: Synchronous file I/O operations inside `async` route definitions (e.g., `with open(...)` in `app/main.py:154`) were blocking the main thread execution and event loop, affecting throughput and scaling under load.
- **Pattern Used**: In-memory dictionary caching mechanism mapping filepaths to strings. First read uses `asyncio.to_thread` to read the file so it does not block the asyncio event loop.
- **Optimization**: Implemented an async `get_template` function combined with a module-level `template_cache` dict to serve commonly accessed static HTML templates directly from memory on repeated requests.
- **Result**: Removed per-request disk I/O, decreasing execution time per request for static pages directly and keeping the asyncio event loop unblocked for concurrent requests.
