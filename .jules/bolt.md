## 2024-06-25 - Offload Synchronous I/O in Async Contexts
**Learning:** Calling synchronous blocking functions (like `storage.delete_file` using `boto3`) inside a FastAPI `async def` endpoint blocks the main event loop. Executing these sequentially amplifies the latency drastically.
**Action:** Use `asyncio.to_thread` and `asyncio.gather` to concurrently offload these blocking calls to a background threadpool, freeing up the event loop and significantly reducing overall execution time.
