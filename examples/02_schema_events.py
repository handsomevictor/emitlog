"""02_schema_events.py — Schema events with field coloring.

Demonstrates:
- @event with all field types
- field() with color and color_map
- event_name snake_case conversion
- Events are valid dataclasses (can use dataclasses.asdict, etc.)
"""

from __future__ import annotations

import asyncio
import dataclasses

import emitlog
from emitlog import event, field
from emitlog.formatters import PrettyFormatter
from emitlog.sinks import Stderr


@event(level="info")
class OrderCreated:
    order_id: str = field(color="cyan")
    amount: float = field(color="bold green")
    status: str = field(color="yellow")


@event(level="info")
class HttpRequest:
    method: str = field(color="bold cyan")
    path: str = field(color="white")
    # color_map: different color based on value range
    status_code: int = field(
        color_map=[
            (range(200, 300), "bold green"),
            (range(300, 400), "cyan"),
            (range(400, 500), "bold yellow"),
            (range(500, 600), "bold red"),
        ]
    )
    duration_ms: float = field(
        color_map=[
            (range(0, 100), "green"),
            (range(100, 500), "yellow"),
            (range(500, 99999), "bold red"),
        ]
    )


@event(level="debug")
class DatabaseQuery:
    sql: str
    rows_returned: int
    duration_ms: float


log = emitlog.get_logger(__name__)


async def main() -> None:
    emitlog.configure(
        sinks=[Stderr(formatter=PrettyFormatter(colorize=True, force_ansi=True))],
        level="debug",
    )

    # OrderCreated — demonstrating field-level colors
    await log.emit(OrderCreated(order_id="ord-123", amount=99.99, status="pending"))
    await log.emit(OrderCreated(order_id="ord-456", amount=1500.00, status="completed"))

    # HttpRequest — demonstrating color_map (value-based colors)
    await log.emit(HttpRequest(method="GET", path="/api/users", status_code=200, duration_ms=45.2))
    await log.emit(HttpRequest(method="POST", path="/api/orders", status_code=201, duration_ms=312.0))
    await log.emit(HttpRequest(method="GET", path="/api/slow", status_code=404, duration_ms=750.5))
    await log.emit(HttpRequest(method="GET", path="/api/broken", status_code=500, duration_ms=12.0))

    # Events are valid dataclasses — you can use standard dataclass tools
    order = OrderCreated(order_id="ord-789", amount=25.0, status="paid")
    print("\nEvent as dict:", dataclasses.asdict(order))
    print("Event name:", order.__emitlog_event_name__)
    print("Event level:", order.__emitlog_level__)


if __name__ == "__main__":
    asyncio.run(main())
