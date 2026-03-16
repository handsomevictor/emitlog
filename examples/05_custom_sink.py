"""05_custom_sink.py — Building a custom sink.

Demonstrates:
- Implementing BaseSink for a custom destination
- Using _serialize() helper from BaseSink
- Custom formatter with BaseSink
- Multiple sinks simultaneously
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import emitlog
from emitlog import event, field
from emitlog._record import LogRecord
from emitlog.formatters import JsonFormatter, PrettyFormatter
from emitlog.sinks import BaseSink, Stderr


@event(level="info")
class PurchaseEvent:
    user_id: int
    product_id: str
    amount: float


@event(level="error")
class PaymentFailed:
    user_id: int
    error_code: str
    message: str


class MemorySink(BaseSink):
    """In-memory sink useful for testing — stores all records."""

    def __init__(self) -> None:
        self.records: list[LogRecord] = []
        self.formatter = JsonFormatter()

    async def write(self, record: LogRecord) -> None:
        self.records.append(record)

    async def close(self) -> None:
        pass  # Nothing to close for in-memory storage


class AlertSink(BaseSink):
    """Custom sink that only forwards error/critical events to an alert system."""

    def __init__(self, alert_levels: set[str] | None = None) -> None:
        self.alert_levels = alert_levels or {"error", "critical"}
        self.alerts: list[dict[str, Any]] = []
        self.formatter = JsonFormatter()

    async def write(self, record: LogRecord) -> None:
        if record.level in self.alert_levels:
            # In a real implementation, this would call PagerDuty, Slack, etc.
            payload = json.loads(self._serialize(record))
            self.alerts.append(payload)
            print(f"  [ALERT] {record.level.upper()}: {record.event_name} → {record.fields}")

    async def close(self) -> None:
        pass


log = emitlog.get_logger(__name__)


async def main() -> None:
    memory = MemorySink()
    alerts = AlertSink()

    # Multiple sinks: pretty output to terminal + memory capture + alert system
    emitlog.configure(
        sinks=[
            Stderr(formatter=PrettyFormatter(colorize=True, force_ansi=True)),
            memory,
            alerts,
        ],
        level="info",
    )

    print("=== Processing purchases ===")
    await log.emit(PurchaseEvent(user_id=1, product_id="prod-001", amount=29.99))
    await log.emit(PurchaseEvent(user_id=2, product_id="prod-002", amount=149.00))
    await log.emit(PaymentFailed(user_id=3, error_code="CARD_DECLINED", message="Card declined"))
    await log.emit(PurchaseEvent(user_id=4, product_id="prod-003", amount=9.99))

    print(f"\nTotal records in memory: {len(memory.records)}")
    print(f"Total alerts triggered: {len(alerts.alerts)}")
    print(f"Alert event names: {[a['event_name'] for a in alerts.alerts]}")


if __name__ == "__main__":
    asyncio.run(main())
