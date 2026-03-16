"""06_fastapi_integration.py — FastAPI middleware integration.

Demonstrates:
- Middleware that auto-injects request_id into every log
- Each log line automatically carries the request_id from context
- Uses httpx.AsyncClient(app=app) to test without starting a real server

Note: Uses in-process testing (no real server) via httpx transport.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import emitlog
from emitlog import event
from emitlog._record import LogRecord
from emitlog.formatters import PrettyFormatter
from emitlog.sinks import BaseSink, Stderr


# ----- Events ---------------------------------------------------------------

@event(level="info")
class RequestReceived:
    method: str
    path: str


@event(level="info")
class RequestCompleted:
    method: str
    path: str
    status_code: int


@event(level="info")
class DatabaseQueryRan:
    query: str
    rows: int


# ----- Memory sink for assertions -------------------------------------------

class MemorySink(BaseSink):
    def __init__(self) -> None:
        self.records: list[LogRecord] = []

    async def write(self, record: LogRecord) -> None:
        self.records.append(record)


# ----- FastAPI app ----------------------------------------------------------

app = FastAPI()
log = emitlog.get_logger("api")


@app.middleware("http")
async def logging_middleware(request: Request, call_next: Any) -> Any:
    """Inject request_id into context for all downstream logs."""
    request_id = str(uuid.uuid4())[:8]
    # All logs inside this context automatically carry request_id
    async with log.context(request_id=request_id, method=request.method):
        await log.emit(RequestReceived(method=request.method, path=request.url.path))
        response = await call_next(request)
        await log.emit(RequestCompleted(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
        ))
    return response


@app.get("/users/{user_id}")
async def get_user(user_id: int) -> JSONResponse:
    # This log automatically has request_id from middleware context
    await log.emit(DatabaseQueryRan(query=f"SELECT * FROM users WHERE id={user_id}", rows=1))
    return JSONResponse({"user_id": user_id, "name": "Alice"})


@app.get("/health")
async def health_check() -> JSONResponse:
    return JSONResponse({"status": "ok"})


# ----- Main -----------------------------------------------------------------

async def main() -> None:
    memory = MemorySink()
    emitlog.configure(
        sinks=[
            Stderr(formatter=PrettyFormatter(colorize=True, force_ansi=True)),
            memory,
        ],
        level="debug",
    )

    # Use httpx.AsyncClient with ASGI transport — no server needed
    transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        print("=== GET /users/42 ===")
        resp = await client.get("/users/42")
        assert resp.status_code == 200

        print("\n=== GET /health ===")
        resp = await client.get("/health")
        assert resp.status_code == 200

        print("\n=== GET /users/99 ===")
        resp = await client.get("/users/99")
        assert resp.status_code == 200

    print(f"\nTotal records captured: {len(memory.records)}")

    # Each request should have request_id in context
    for record in memory.records:
        if record.context:
            print(f"  {record.event_name}: request_id={record.context.get('request_id', 'N/A')}")

    # Verify all records have request_id
    records_with_context = [r for r in memory.records if r.context.get("request_id")]
    print(f"\nRecords with request_id: {len(records_with_context)}/{len(memory.records)}")
    assert len(records_with_context) == len(memory.records), "All records should have request_id!"
    print("✓ All records have request_id injected by middleware")


if __name__ == "__main__":
    asyncio.run(main())
