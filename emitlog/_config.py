"""Global configuration singleton for emitlog.

Loggers do NOT hold config; they read the global config at emit time.
configure() is protected by threading.Lock.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from emitlog.sinks._base import BaseSink

__all__ = ["get_config", "configure", "_GlobalConfig"]

_LEVEL_ORDER: dict[str, int] = {
    "debug": 10,
    "info": 20,
    "warning": 30,
    "error": 40,
    "critical": 50,
}


@dataclass
class _GlobalConfig:
    """Mutable global configuration for emitlog."""

    sinks: list["BaseSink"] = field(default_factory=list)
    level: str = "info"
    capture_stdlib: bool = False
    _stdlib_handler: Any = field(default=None, repr=False)

    def level_enabled(self, level: str) -> bool:
        """Return True if the given level is at or above the configured level."""
        return _LEVEL_ORDER.get(level, 0) >= _LEVEL_ORDER.get(self.level, 0)


_config = _GlobalConfig()
_config_lock = threading.Lock()


def get_config() -> _GlobalConfig:
    """Return the current global configuration (not a copy — do not mutate)."""
    return _config


def configure(
    *,
    sinks: "list[BaseSink] | None" = None,
    level: str = "info",
    capture_stdlib: bool = False,
) -> None:
    """Replace the global emitlog configuration.

    Parameters
    ----------
    sinks:
        List of sinks to write to.  If None, a default ``Stderr()`` sink is
        used.
    level:
        Minimum log level.  One of: ``debug | info | warning | error | critical``.
    capture_stdlib:
        If True, register a handler on the stdlib root logger that forwards
        records to emitlog.
    """
    import asyncio

    from emitlog.sinks._stderr import Stderr

    with _config_lock:
        global _config

        old_config = _config

        # Close old sinks (fire-and-forget; they may not need async)
        for sink in old_config.sinks:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(sink.close())
                else:
                    loop.run_until_complete(sink.close())
            except Exception:
                pass

        # Remove old stdlib handler if any
        if old_config._stdlib_handler is not None:
            import logging

            logging.root.removeHandler(old_config._stdlib_handler)

        effective_sinks: list[BaseSink] = sinks if sinks is not None else [Stderr()]

        new_config = _GlobalConfig(
            sinks=effective_sinks,
            level=level.lower(),
            capture_stdlib=capture_stdlib,
        )

        if capture_stdlib:
            from emitlog._compat import _EmitlogHandler

            handler = _EmitlogHandler()
            import logging

            logging.root.addHandler(handler)
            logging.root.setLevel(logging.DEBUG)
            new_config._stdlib_handler = handler

        _config = new_config
