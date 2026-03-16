"""Logger class: the primary emitlog interface.

Do NOT inherit from stdlib logging.Logger.
"""

from __future__ import annotations

import asyncio
import dataclasses
from datetime import datetime, timezone
from typing import Any

from emitlog._context import _ContextManager, get_current_context
from emitlog._event import _EMITLOG_META_KEY
from emitlog._record import LogRecord
from emitlog._sampling import should_emit
from emitlog._span import Span, SpanList

__all__ = ["Logger", "get_logger"]

_loggers: dict[str, "Logger"] = {}


def _make_timestamp() -> str:
    """Return current UTC time as ISO 8601 with milliseconds."""
    now = datetime.now(tz=timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _to_plain(value: Any) -> Any:
    """Convert Span/SpanList to plain text string; leave other values unchanged."""
    if isinstance(value, (Span, SpanList)):
        return str(value)
    return value


class Logger:
    """An emitlog logger.

    Loggers are created via :func:`get_logger`.  They do NOT hold configuration
    — configuration is read from the global config at emit time.
    """

    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def context(self, **fields: Any) -> _ContextManager:
        """Return a context manager that injects ``fields`` into the log context.

        Supports both ``async with`` and ``with`` syntax.
        """
        return _ContextManager(**fields)

    async def emit(self, event_obj: Any) -> None:
        """Emit a structured log event asynchronously.

        Parameters
        ----------
        event_obj:
            An instance of a class decorated with :func:`@event`.

        Raises
        ------
        TypeError
            If ``event_obj`` is not an ``@event``-decorated instance.
        """
        if not hasattr(event_obj, "__emitlog_level__"):
            raise TypeError(
                f"emit() requires an @event-decorated instance, got {type(event_obj)!r}. "
                "Use @event to decorate your event classes."
            )

        from emitlog._config import get_config

        config = get_config()
        level: str = event_obj.__emitlog_level__
        sample_rate: float = event_obj.__emitlog_sample_rate__
        sample_by: str | None = event_obj.__emitlog_sample_by__
        event_name: str = event_obj.__emitlog_event_name__
        field_meta: dict[str, Any] = event_obj.__emitlog_field_meta__

        # Level filter
        if not config.level_enabled(level):
            return

        # Build raw fields from dataclass
        raw_fields: dict[str, Any] = {}
        for f in dataclasses.fields(event_obj):
            raw_fields[f.name] = getattr(event_obj, f.name)

        # Sampling (before serialization)
        if not should_emit(sample_rate, sample_by, raw_fields):
            return

        # Build plain fields (Span/SpanList → str)
        plain_fields: dict[str, Any] = {k: _to_plain(v) for k, v in raw_fields.items()}

        # Context snapshot
        context = get_current_context()

        record = LogRecord(
            timestamp=_make_timestamp(),
            level=level,
            logger_name=self._name,
            event_name=event_name,
            fields=plain_fields,
            raw_fields=raw_fields,
            context=context,
        )

        # Attach field_meta for formatters that need it (PrettyFormatter)
        # We use object.__setattr__ because LogRecord is frozen
        # Instead, pass field_meta via a wrapper mechanism:
        # We use a subclass trick — set it as a non-frozen attr via object.__setattr__
        try:
            object.__setattr__(record, "_field_meta", field_meta)
        except Exception:
            pass

        # Write to all sinks
        for sink in config.sinks:
            await sink.write(record)

    def emit_sync(self, event_obj: Any) -> None:
        """Emit a structured log event synchronously.

        If called from within a running coroutine, raises ``RuntimeError``
        suggesting ``await log.emit()`` instead.
        If called outside a coroutine, runs the async emit via ``asyncio.run()``.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            raise RuntimeError(
                "emit_sync() was called from within an async context. "
                "Use 'await log.emit(...)' instead."
            )

        asyncio.run(self.emit(event_obj))


def get_logger(name: str) -> Logger:
    """Return (or create) a :class:`Logger` with the given name.

    This function is safe to call at import time — it does NOT trigger any
    IO or configuration reads.

    Parameters
    ----------
    name:
        Logger name, typically ``__name__``.
    """
    if name not in _loggers:
        _loggers[name] = Logger(name)
    return _loggers[name]
