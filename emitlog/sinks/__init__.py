"""emitlog.sinks public API."""

from __future__ import annotations

from emitlog.sinks._base import BaseSink
from emitlog.sinks._file import AsyncFile, File
from emitlog.sinks._stderr import Stderr

__all__ = [
    "BaseSink",
    "Stderr",
    "File",
    "AsyncFile",
]
