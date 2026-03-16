"""01_quickstart.py — Getting started with emitlog.

Demonstrates:
- Defining events with @event decorator
- Zero-config logging (auto-selects Pretty or JSON based on terminal)
- Using get_logger() at module level (safe at import time — no IO)
- emit() and emit_sync() usage
"""

from __future__ import annotations

import asyncio

import emitlog
from emitlog import event, field
from emitlog.formatters import PrettyFormatter
from emitlog.sinks import Stderr


# Define events at module level — safe, no IO triggered
@event(level="info")
class AppStarted:
    version: str
    environment: str


@event(level="info")
class UserLogin:
    user_id: int
    ip: str
    user_agent: str = ""


@event(level="warning")
class RateLimitExceeded:
    user_id: int
    requests_per_minute: int


# Get a logger — also safe at import time
log = emitlog.get_logger(__name__)


async def main() -> None:
    # Configure emitlog — force PrettyFormatter so output is human-readable
    # regardless of whether stdout is a tty.
    emitlog.configure(
        sinks=[Stderr(formatter=PrettyFormatter(colorize=True, force_ansi=True))],
        level="debug",
    )

    # Emit events asynchronously (primary interface)
    await log.emit(AppStarted(version="1.0.0", environment="production"))
    await log.emit(UserLogin(user_id=42, ip="192.168.1.1", user_agent="Mozilla/5.0"))
    await log.emit(RateLimitExceeded(user_id=42, requests_per_minute=120))


if __name__ == "__main__":
    asyncio.run(main())
