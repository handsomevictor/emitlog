"""03_context.py — Context propagation via contextvars.

Demonstrates:
- log.context() as async context manager
- log.context() as sync context manager
- Nested contexts (inner overrides outer same-name fields)
- Context restored after exception
- asyncio.gather context isolation
"""

from __future__ import annotations

import asyncio

import emitlog
from emitlog import event, field
from emitlog.formatters import PrettyFormatter
from emitlog.sinks import Stderr


@event(level="info")
class RequestProcessed:
    path: str
    status: int


@event(level="info")
class TaskCompleted:
    task_id: str
    result: str


log = emitlog.get_logger(__name__)


async def handle_request(request_id: str, path: str) -> None:
    # Each request gets its own context — automatically included in all logs
    async with log.context(request_id=request_id, service="api"):
        await log.emit(RequestProcessed(path=path, status=200))

        # Nested context: inner fields override outer same-name fields
        async with log.context(service="database"):
            await log.emit(TaskCompleted(task_id="db-query-1", result="ok"))
            # Both request_id and service="database" are in context

        # After inner context exits, service="api" is restored
        await log.emit(TaskCompleted(task_id="cleanup", result="ok"))


async def main() -> None:
    emitlog.configure(
        sinks=[Stderr(formatter=PrettyFormatter(colorize=True, force_ansi=True))],
        level="debug",
    )

    print("=== Sequential requests ===")
    await handle_request("req-001", "/api/users")
    await handle_request("req-002", "/api/orders")

    print("\n=== Parallel requests (isolated contexts) ===")
    # asyncio.gather: each coroutine has its own context copy
    # request_id from task_a does NOT leak into task_b
    await asyncio.gather(
        handle_request("req-003", "/api/a"),
        handle_request("req-004", "/api/b"),
    )

    print("\n=== Sync context manager ===")
    # emit_sync() must be called outside an async context
    # To demonstrate sync context, we define a sync function here
    def run_sync_batch() -> None:
        with log.context(job_id="batch-001"):
            # emit_sync() works when not inside a running event loop
            log.emit_sync(RequestProcessed(path="/batch/run", status=202))

    # Run in a thread to avoid the "inside async context" restriction
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as pool:
        future = pool.submit(run_sync_batch)
        future.result()


if __name__ == "__main__":
    asyncio.run(main())
