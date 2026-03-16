"""BaseSink abstract class for emitlog output sinks."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from emitlog._record import LogRecord
from emitlog._serializer import serialize

if TYPE_CHECKING:
    from emitlog.formatters._base import BaseFormatter

__all__ = ["BaseSink"]


class BaseSink(ABC):
    """Abstract base class for all emitlog sinks.

    Subclasses must implement :meth:`write`.
    The :meth:`_serialize` helper is provided for convenience.

    Subclasses may optionally set ``self.formatter`` (a :class:`BaseFormatter`)
    which :meth:`_serialize` will use instead of the default JSON serializer.
    """

    formatter: "BaseFormatter | None" = None

    def _serialize(self, record: LogRecord) -> str:
        """Serialize a record to a string using the configured formatter.

        Falls back to JSON serialization if no formatter is attached.
        """
        if self.formatter is not None:
            return self.formatter.format(record)
        return serialize(record)

    @abstractmethod
    async def write(self, record: LogRecord) -> None:
        """Write a log record to this sink."""
        ...

    async def close(self) -> None:
        """Close this sink and release any resources."""
        pass
