"""Context propagation via contextvars.

Provides a context manager (both sync and async) that merges new fields into
the current context, with proper restoration on exit even when exceptions occur.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from types import TracebackType
from typing import Any

__all__ = ["_ctx", "get_current_context", "_ContextManager"]

_ctx: ContextVar[dict[str, Any]] = ContextVar("emitlog_ctx", default={})


def get_current_context() -> dict[str, Any]:
    """Return a copy of the current context dict."""
    return dict(_ctx.get())


class _ContextManager:
    """Context manager that merges fields into the current emitlog context.

    Supports both ``async with`` and ``with`` usage.

    - Enter: merged = {**current, **new_fields}, save token
    - Exit: var.reset(token), regardless of exceptions
    - asyncio.gather contexts are isolated because each coroutine inherits its
      own copy of the context at creation time (standard contextvars behaviour).
    """

    __slots__ = ("_fields", "_token")

    def __init__(self, **fields: Any) -> None:
        self._fields = fields
        self._token: Token[dict[str, Any]] | None = None

    def _enter(self) -> "_ContextManager":
        merged = {**_ctx.get(), **self._fields}
        self._token = _ctx.set(merged)
        return self

    def _exit(self) -> None:
        if self._token is not None:
            _ctx.reset(self._token)
            self._token = None

    # Sync context manager
    def __enter__(self) -> "_ContextManager":
        return self._enter()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._exit()

    # Async context manager
    async def __aenter__(self) -> "_ContextManager":
        return self._enter()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._exit()
