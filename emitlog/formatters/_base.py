"""BaseFormatter abstract class."""

from __future__ import annotations

from abc import ABC, abstractmethod

from emitlog._record import LogRecord

__all__ = ["BaseFormatter"]


class BaseFormatter(ABC):
    """Abstract base class for all emitlog formatters.

    Subclasses must implement :meth:`format`.
    """

    @abstractmethod
    def format(self, record: LogRecord) -> str:
        """Convert a ``LogRecord`` to a string for output."""
        ...
