"""emitlog — asyncio-first, type-safe, structured logging for Python microservices."""

from __future__ import annotations

from emitlog._config import configure
from emitlog._event import event, field
from emitlog._logger import get_logger
from emitlog._span import colored, markup, span

__all__ = [
    "get_logger",
    "configure",
    "event",
    "field",
    "colored",
    "span",
    "markup",
]

__version__ = "0.1.0"
