"""emitlog — asyncio-first, type-safe, structured logging for Python microservices."""

from __future__ import annotations

import sys

if sys.version_info < (3, 13):
    raise RuntimeError(
        f"emitlog requires Python 3.13 or later.\n"
        f"You are running Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}.\n"
        f"\n"
        f"Please upgrade: https://www.python.org/downloads/\n"
        f"Or install via uv which manages Python versions automatically:\n"
        f"  uv pip install emitlog"
    )

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
