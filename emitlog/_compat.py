"""Stdlib logging compatibility layer.

Registers a handler with the stdlib root logger that forwards records to
emitlog.  Avoids circular logging by skipping records from emitlog itself.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

__all__ = ["_EmitlogHandler"]


def _write_record_sync(record: "Any") -> None:
    """Write a LogRecord to all configured sinks synchronously."""
    from emitlog._config import get_config

    config = get_config()
    for sink in config.sinks:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            # Schedule as fire-and-forget task
            loop.create_task(sink.write(record))
        else:
            # Create a new event loop to run the coroutine
            asyncio.run(sink.write(record))


class _EmitlogHandler(logging.Handler):
    """Stdlib logging.Handler that bridges to emitlog."""

    def emit(self, record: logging.LogRecord) -> None:
        # Avoid circular logging
        if record.name.startswith("emitlog"):
            return

        from emitlog._config import get_config
        from emitlog._record import LogRecord

        # Map stdlib level to emitlog level
        level_name = record.levelname.lower()
        if level_name == "warn":
            level_name = "warning"

        # Build timestamp
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        timestamp = dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"

        fields: dict[str, Any] = {
            "message": record.getMessage(),
            "logger": record.name,
        }

        log_record = LogRecord(
            timestamp=timestamp,
            level=level_name,
            logger_name="stdlib",
            event_name="stdlib_log",
            fields=fields,
            raw_fields=dict(fields),
            context={},
        )

        config = get_config()
        if not config.level_enabled(level_name):
            return

        # Write to all sinks synchronously
        for sink in config.sinks:
            try:
                # Try to get the running loop
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None

                if loop is not None and loop.is_running():
                    # Inside an async context: schedule task
                    loop.create_task(sink.write(log_record))
                else:
                    # Outside async: use asyncio.run
                    asyncio.run(sink.write(log_record))
            except Exception:
                pass
