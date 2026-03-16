"""04_sampling.py — Event sampling to reduce log volume.

Demonstrates:
- sample_rate=1.0 (default): log everything
- sample_rate=0.01: log ~1% of events
- sample_by="user_id": deterministic per-user sampling
  (same user_id always makes the same sampling decision)
"""

from __future__ import annotations

import asyncio

import emitlog
from emitlog import event, field
from emitlog.formatters import PrettyFormatter
from emitlog.sinks import Stderr


@event(level="info", sample_rate=0.01)
class HealthCheckCalled:
    """Emitted for every health check — but sampled at 1%."""
    pass


@event(level="info", sample_rate=0.1, sample_by="user_id")
class ApiCalled:
    """Sampled at 10% per user. Same user_id always same sampling decision."""
    user_id: int
    endpoint: str


@event(level="info")
class ImportantEvent:
    """Always logged — sample_rate defaults to 1.0."""
    order_id: str


log = emitlog.get_logger(__name__)


async def main() -> None:
    emitlog.configure(
        sinks=[Stderr(formatter=PrettyFormatter(colorize=True, force_ansi=True))],
        level="debug",
    )

    # HealthCheckCalled: 1% sample rate — most will be dropped
    print("=== Health checks (1% sample rate, 100 calls) ===")
    emitted = 0
    for _ in range(100):
        before = 0  # We'll count by running differently
        await log.emit(HealthCheckCalled())

    # Count by using a memory sink
    from emitlog._record import LogRecord
    from emitlog.sinks import BaseSink

    class CountSink(BaseSink):
        def __init__(self) -> None:
            self.count = 0
        async def write(self, record: LogRecord) -> None:
            self.count += 1

    counter = CountSink()
    emitlog.configure(sinks=[counter], level="debug")

    for _ in range(1000):
        await log.emit(HealthCheckCalled())

    print(f"HealthCheckCalled: 1000 calls, ~{counter.count} emitted (expected ~10)")

    # ApiCalled: deterministic per-user sampling
    # Users with same ID always make the same decision
    counter2 = CountSink()
    emitlog.configure(sinks=[counter2], level="debug")

    for i in range(100):
        await log.emit(ApiCalled(user_id=i % 20, endpoint="/api/test"))

    print(f"ApiCalled: 100 calls, ~{counter2.count} emitted (expected ~10)")

    # ImportantEvent: always logged
    counter3 = CountSink()
    emitlog.configure(sinks=[counter3], level="debug")

    for i in range(50):
        await log.emit(ImportantEvent(order_id=f"ord-{i}"))

    print(f"ImportantEvent: 50 calls, {counter3.count} emitted (expected 50)")

    # Deterministic sampling: same user_id always same result
    counter4a = CountSink()
    counter4b = CountSink()
    emitlog.configure(sinks=[counter4a], level="debug")
    for i in range(100):
        await log.emit(ApiCalled(user_id=42, endpoint="/api/test"))
    emitlog.configure(sinks=[counter4b], level="debug")
    for i in range(100):
        await log.emit(ApiCalled(user_id=42, endpoint="/api/test"))

    assert counter4a.count == counter4b.count, "Same user_id should have same sampling result!"
    print(f"Deterministic: user_id=42 always {'passes' if counter4a.count > 0 else 'drops'} (consistent)")


if __name__ == "__main__":
    asyncio.run(main())
