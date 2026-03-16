"""JSON formatter: serializes LogRecord as a single-line JSON string."""

from __future__ import annotations

from emitlog._record import LogRecord
from emitlog._serializer import serialize
from emitlog.formatters._base import BaseFormatter

__all__ = ["JsonFormatter"]


class JsonFormatter(BaseFormatter):
    """Formatter that produces single-line JSON output.

    Span/SpanList values in ``record.fields`` are already converted to plain
    text in the ``LogRecord``.  The JSON output uses the field ordering:
    timestamp → level → logger_name → event_name → **fields → **context.
    """

    def format(self, record: LogRecord) -> str:
        """Return the record as a JSON string (no trailing newline)."""
        return serialize(record)
