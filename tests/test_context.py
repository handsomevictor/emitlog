"""Tests for _context.py."""

from __future__ import annotations

import asyncio

import pytest

from emitlog._context import _ContextManager, get_current_context


class TestContextSync:
    def test_single_layer_context_injected(self) -> None:
        with _ContextManager(request_id="abc", service="order"):
            ctx = get_current_context()
        assert ctx["request_id"] == "abc"
        assert ctx["service"] == "order"

    def test_context_restored_after_exit(self) -> None:
        with _ContextManager(x=1):
            pass
        ctx = get_current_context()
        assert "x" not in ctx

    def test_nested_inner_overrides_outer(self) -> None:
        with _ContextManager(key="outer", other="keep"):
            with _ContextManager(key="inner"):
                ctx = get_current_context()
                assert ctx["key"] == "inner"
                assert ctx["other"] == "keep"

    def test_nested_outer_restored_after_inner_exit(self) -> None:
        with _ContextManager(key="outer"):
            with _ContextManager(key="inner"):
                pass
            ctx = get_current_context()
            assert ctx["key"] == "outer"

    def test_exception_restores_context(self) -> None:
        try:
            with _ContextManager(x=99):
                raise ValueError("boom")
        except ValueError:
            pass
        ctx = get_current_context()
        assert "x" not in ctx

    def test_sync_context_manager_works(self) -> None:
        ctx_mgr = _ContextManager(job_id="batch-001")
        with ctx_mgr:
            inner = get_current_context()
        assert inner["job_id"] == "batch-001"
        outer = get_current_context()
        assert "job_id" not in outer


class TestContextAsync:
    @pytest.mark.asyncio
    async def test_async_single_layer(self) -> None:
        async with _ContextManager(request_id="xyz"):
            ctx = get_current_context()
        assert ctx["request_id"] == "xyz"

    @pytest.mark.asyncio
    async def test_async_nested(self) -> None:
        async with _ContextManager(a=1):
            async with _ContextManager(b=2):
                ctx = get_current_context()
                assert ctx["a"] == 1
                assert ctx["b"] == 2
            ctx_after = get_current_context()
            assert ctx_after["a"] == 1
            assert "b" not in ctx_after

    @pytest.mark.asyncio
    async def test_async_exception_restores(self) -> None:
        try:
            async with _ContextManager(x=99):
                raise RuntimeError("async boom")
        except RuntimeError:
            pass
        ctx = get_current_context()
        assert "x" not in ctx

    @pytest.mark.asyncio
    async def test_context_isolation_in_gather(self) -> None:
        """asyncio.gather two coroutines contexts must be isolated."""
        results: dict[str, dict[str, object]] = {}

        async def task_a() -> None:
            async with _ContextManager(task="a", value=1):
                await asyncio.sleep(0.01)
                results["a"] = dict(get_current_context())

        async def task_b() -> None:
            async with _ContextManager(task="b", value=2):
                await asyncio.sleep(0.01)
                results["b"] = dict(get_current_context())

        await asyncio.gather(task_a(), task_b())

        assert results["a"]["task"] == "a"
        assert results["a"]["value"] == 1
        assert results["b"]["task"] == "b"
        assert results["b"]["value"] == 2
