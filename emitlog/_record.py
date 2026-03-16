"""LogRecord dataclass: the immutable value object that flows through the pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LogRecord:
    """Immutable record produced for each emitted event.

    Attributes
    ----------
    timestamp:
        ISO 8601 UTC with milliseconds, e.g. ``2024-01-15T10:23:45.123Z``.
    level:
        Lowercase level string: ``debug | info | warning | error | critical``.
    logger_name:
        Name passed to ``get_logger()``.
    event_name:
        Class name converted to snake_case, e.g. ``UserLogin → user_login``.
    fields:
        Event fields with ``Span``/``SpanList`` converted to plain text.
    raw_fields:
        Original event fields; may contain ``Span``/``SpanList`` objects.
    context:
        Snapshot of the contextvars context at emit time.
    """

    timestamp: str
    level: str
    logger_name: str
    event_name: str
    fields: dict[str, Any]
    raw_fields: dict[str, Any]
    context: dict[str, Any]
