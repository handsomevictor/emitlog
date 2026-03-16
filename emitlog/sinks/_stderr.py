"""Stderr sink: writes formatted log records to sys.stderr."""

from __future__ import annotations

import sys

from emitlog._record import LogRecord
from emitlog.formatters._base import BaseFormatter
from emitlog.sinks._base import BaseSink

__all__ = ["Stderr"]


class Stderr(BaseSink):
    """Sink that writes log records to ``sys.stderr``.

    Parameters
    ----------
    formatter:
        Formatter to use.  If ``None``, automatically selects
        :class:`~emitlog.formatters.PrettyFormatter` when the terminal is a
        tty or ``EMITLOG_DEV=1`` is set, otherwise
        :class:`~emitlog.formatters.JsonFormatter`.
    """

    def __init__(self, formatter: BaseFormatter | None = None) -> None:
        self.formatter = formatter

    def _get_formatter(self) -> BaseFormatter:
        if self.formatter is not None:
            return self.formatter
        import os

        from emitlog.formatters._json import JsonFormatter
        from emitlog.formatters._pretty import PrettyFormatter

        if sys.stderr.isatty() or os.environ.get("EMITLOG_DEV") == "1":
            return PrettyFormatter()
        return JsonFormatter()

    async def write(self, record: LogRecord) -> None:
        """Write the formatted record to stderr."""
        formatter = self._get_formatter()
        line = formatter.format(record)
        print(line, file=sys.stderr)

    async def close(self) -> None:
        """Stderr does not need explicit closing."""
        pass
