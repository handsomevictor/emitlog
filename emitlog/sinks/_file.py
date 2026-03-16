"""File sinks: synchronous File and async AsyncFile."""

from __future__ import annotations

import asyncio
import io
import os
from pathlib import Path
from typing import Any

from emitlog._record import LogRecord
from emitlog.formatters._base import BaseFormatter
from emitlog.sinks._base import BaseSink

__all__ = ["File", "AsyncFile"]


class File(BaseSink):
    """Synchronous file sink (opens file in append mode).

    This sink writes synchronously.  For high-throughput scenarios prefer
    :class:`AsyncFile`.

    Parameters
    ----------
    path:
        Path to the log file.
    formatter:
        Formatter to use.  Defaults to :class:`~emitlog.formatters.JsonFormatter`.
    """

    def __init__(
        self,
        path: str | Path,
        formatter: BaseFormatter | None = None,
    ) -> None:
        self.path = Path(path)
        if formatter is None:
            from emitlog.formatters._json import JsonFormatter

            self.formatter: BaseFormatter = JsonFormatter()
        else:
            self.formatter = formatter
        self._file: io.TextIOWrapper | None = None

    def _ensure_open(self) -> None:
        if self._file is None or self._file.closed:
            self._file = open(self.path, "a", encoding="utf-8")

    async def write(self, record: LogRecord) -> None:
        """Write the record to the file."""
        self._ensure_open()
        assert self._file is not None
        line = self.formatter.format(record)
        self._file.write(line + "\n")
        self._file.flush()

    async def close(self) -> None:
        """Close the underlying file."""
        if self._file and not self._file.closed:
            self._file.close()


class AsyncFile(BaseSink):
    """Async buffered file sink using an asyncio queue.

    The background consumer task is lazily started on the first
    :meth:`write` call, not in ``__init__``.

    Parameters
    ----------
    path:
        Path to the log file.
    formatter:
        Formatter to use.  Defaults to :class:`~emitlog.formatters.JsonFormatter`.
    maxsize:
        Maximum number of records to buffer in the queue.
    overflow_policy:
        ``"drop"`` silently discards new records when the queue is full.
        ``"block"`` waits until there is space.
    rotate:
        Optional rotation config, e.g.
        ``{"type": "size", "max_bytes": 10_000_000}`` or
        ``{"type": "time", "when": "midnight"}``.
    """

    _SENTINEL: object = object()

    def __init__(
        self,
        path: str | Path,
        formatter: BaseFormatter | None = None,
        maxsize: int = 10_000,
        overflow_policy: str = "drop",
        rotate: dict[str, Any] | None = None,
    ) -> None:
        self.path = Path(path)
        if formatter is None:
            from emitlog.formatters._json import JsonFormatter

            self.formatter: BaseFormatter = JsonFormatter()
        else:
            self.formatter = formatter
        self.maxsize = maxsize
        self.overflow_policy = overflow_policy
        self.rotate = rotate

        # Lazily initialized
        self._queue: asyncio.Queue[object] | None = None
        self._task: asyncio.Task[None] | None = None
        self._file: io.TextIOWrapper | None = None

    def _ensure_started(self) -> None:
        """Lazily start the background consumer task."""
        if self._queue is None:
            self._queue = asyncio.Queue(maxsize=self.maxsize)
            self._task = asyncio.create_task(self._consumer())

    def _open_file(self) -> io.TextIOWrapper:
        return open(self.path, "a", encoding="utf-8")

    async def _consumer(self) -> None:
        """Background task that drains the queue and writes to file."""
        self._file = self._open_file()
        try:
            while True:
                item = await self._queue.get()  # type: ignore[union-attr]
                if item is self._SENTINEL:
                    self._queue.task_done()  # type: ignore[union-attr]
                    break
                if isinstance(item, LogRecord):
                    line = self.formatter.format(item)
                    self._file.write(line + "\n")
                    self._file.flush()
                self._queue.task_done()  # type: ignore[union-attr]
        finally:
            if self._file and not self._file.closed:
                self._file.close()

    async def write(self, record: LogRecord) -> None:
        """Enqueue a record for async writing."""
        self._ensure_started()
        assert self._queue is not None
        if self.overflow_policy == "drop":
            try:
                self._queue.put_nowait(record)
            except asyncio.QueueFull:
                pass  # Drop silently
        else:
            await self._queue.put(record)

    async def close(self) -> None:
        """Drain the queue and close the file."""
        if self._queue is not None:
            await self._queue.put(self._SENTINEL)
            await self._queue.join()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
