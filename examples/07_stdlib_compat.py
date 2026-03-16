"""07_stdlib_compat.py — Capturing stdlib logging output.

Demonstrates:
- capture_stdlib=True: bridges stdlib logging to emitlog sinks
- Existing code using Python's logging module works without changes
- emitlog's own internal logs are NOT captured (no circular loop)
- Reconfiguring emitlog removes the old stdlib handler
"""

from __future__ import annotations

import asyncio
import logging

import emitlog
from emitlog.formatters import PrettyFormatter
from emitlog.sinks import Stderr


async def main() -> None:
    emitlog.configure(
        sinks=[Stderr(formatter=PrettyFormatter(colorize=True, force_ansi=True))],
        level="debug",
        capture_stdlib=True,  # Forward all stdlib logs to emitlog sinks
    )

    print("=== Stdlib logging captured by emitlog ===\n")

    # These use Python's built-in logging module — they get forwarded to emitlog
    db_logger = logging.getLogger("myapp.database")
    http_logger = logging.getLogger("myapp.http")
    third_party = logging.getLogger("requests")

    db_logger.info("Connected to database")
    http_logger.warning("Slow response: 1200ms")
    db_logger.error("Query timeout: SELECT * FROM large_table")
    third_party.debug("HTTP GET https://api.example.com/v1/data")

    # Give async tasks time to run
    await asyncio.sleep(0.05)

    print("\n=== Reconfigure to disable stdlib capture ===\n")
    emitlog.configure(
        sinks=[Stderr(formatter=PrettyFormatter(colorize=True, force_ansi=True))],
        level="debug",
        capture_stdlib=False,
    )

    # These will NOT be captured anymore
    db_logger.info("This message is NOT forwarded to emitlog")
    print("\n(No more stdlib messages above)")


if __name__ == "__main__":
    asyncio.run(main())
