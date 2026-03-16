"""Tests for _logger.py: Logger, get_logger, emit, emit_sync, context."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

import emitlog
from emitlog._event import event, field
from emitlog._logger import get_logger
from emitlog._span import colored
from emitlog.formatters import JsonFormatter
from emitlog.sinks import BaseSink
from emitlog._record import LogRecord


class MemorySink(BaseSink):
    """Captures records in memory for testing."""

    def __init__(self) -> None:
        self.records: list[LogRecord] = []
        self.formatter = JsonFormatter()

    async def write(self, record: LogRecord) -> None:
        self.records.append(record)


@pytest.fixture()
def sink() -> MemorySink:
    s = MemorySink()
    emitlog.configure(sinks=[s], level="debug")
    return s


@event(level="info")
class UserLogin:
    user_id: int
    ip: str


@event(level="debug")
class DebugEvent:
    msg: str


@event(level="warning")
class WarningEvt:
    reason: str


@event(level="info", sample_rate=0.0)
class AlwaysDropped:
    x: int


class TestGetLogger:
    def test_returns_logger(self) -> None:
        log = get_logger("test")
        assert log.name == "test"

    def test_same_name_same_instance(self) -> None:
        a = get_logger("same")
        b = get_logger("same")
        assert a is b


class TestEmit:
    @pytest.mark.asyncio
    async def test_emit_event_works(self, sink: MemorySink) -> None:
        log = get_logger("test_emit")
        await log.emit(UserLogin(user_id=1, ip="1.2.3.4"))
        assert len(sink.records) == 1
        r = sink.records[0]
        assert r.event_name == "user_login"
        assert r.fields["user_id"] == 1
        assert r.level == "info"

    @pytest.mark.asyncio
    async def test_emit_non_event_raises_typeerror(self, sink: MemorySink) -> None:
        log = get_logger("test_type")

        class NotAnEvent:
            pass

        with pytest.raises(TypeError, match="@event"):
            await log.emit(NotAnEvent())

    @pytest.mark.asyncio
    async def test_level_filtering(self, sink: MemorySink) -> None:
        emitlog.configure(sinks=[sink], level="warning")
        log = get_logger("test_filter")
        await log.emit(UserLogin(user_id=1, ip="x"))  # info < warning → filtered
        assert len(sink.records) == 0
        await log.emit(WarningEvt(reason="test"))  # warning = warning → pass
        assert len(sink.records) == 1

    @pytest.mark.asyncio
    async def test_sampling_zero_drops_all(self, sink: MemorySink) -> None:
        log = get_logger("test_sampling")
        for _ in range(10):
            await log.emit(AlwaysDropped(x=1))
        assert len(sink.records) == 0

    @pytest.mark.asyncio
    async def test_context_injected(self, sink: MemorySink) -> None:
        log = get_logger("test_ctx")
        async with log.context(request_id="req-001"):
            await log.emit(UserLogin(user_id=2, ip="2.2.2.2"))
        assert sink.records[0].context["request_id"] == "req-001"

    @pytest.mark.asyncio
    async def test_nested_context(self, sink: MemorySink) -> None:
        log = get_logger("test_nested_ctx")
        async with log.context(a=1):
            async with log.context(b=2):
                await log.emit(UserLogin(user_id=3, ip="x"))
        r = sink.records[0]
        assert r.context["a"] == 1
        assert r.context["b"] == 2

    @pytest.mark.asyncio
    async def test_span_field_plain_in_fields(self, sink: MemorySink) -> None:
        @event(level="info")
        class MsgEvt:
            message: str

        log = get_logger("test_span")
        msg = colored("hello", "green")
        await log.emit(MsgEvt(message=msg))  # type: ignore[arg-type]
        r = sink.records[0]
        assert r.fields["message"] == "hello"  # plain text in fields
        assert r.raw_fields["message"] is msg  # Span preserved in raw_fields

    @pytest.mark.asyncio
    async def test_logger_name_in_record(self, sink: MemorySink) -> None:
        log = get_logger("mymodule.submodule")
        await log.emit(UserLogin(user_id=99, ip="x"))
        assert sink.records[0].logger_name == "mymodule.submodule"

    @pytest.mark.asyncio
    async def test_timestamp_format(self, sink: MemorySink) -> None:
        log = get_logger("ts_test")
        await log.emit(UserLogin(user_id=1, ip="x"))
        ts = sink.records[0].timestamp
        assert ts.endswith("Z")
        assert "T" in ts

    @pytest.mark.asyncio
    async def test_gather_context_isolation(self, sink: MemorySink) -> None:
        """Context is isolated between gather coroutines."""
        results: dict[str, dict[str, object]] = {}
        log = get_logger("test_gather")

        async def task_a() -> None:
            async with log.context(task="a", value=1):
                await asyncio.sleep(0.01)
                await log.emit(UserLogin(user_id=1, ip="a"))
                results["a"] = dict(sink.records[-1].context)

        async def task_b() -> None:
            async with log.context(task="b", value=2):
                await asyncio.sleep(0.01)
                await log.emit(UserLogin(user_id=2, ip="b"))
                results["b"] = dict(sink.records[-1].context)

        await asyncio.gather(task_a(), task_b())
        assert results["a"]["task"] == "a"
        assert results["b"]["task"] == "b"


class TestEmitSync:
    def test_emit_sync_works(self, sink: MemorySink) -> None:
        log = get_logger("sync_test")
        log.emit_sync(UserLogin(user_id=10, ip="3.3.3.3"))
        assert len(sink.records) == 1

    @pytest.mark.asyncio
    async def test_emit_sync_in_async_raises(self, sink: MemorySink) -> None:
        log = get_logger("sync_async_test")
        with pytest.raises(RuntimeError, match="async context"):
            log.emit_sync(UserLogin(user_id=11, ip="x"))


class TestContextManager:
    def test_sync_context_works(self, sink: MemorySink) -> None:
        log = get_logger("sync_ctx")

        async def run() -> None:
            with log.context(job_id="batch-001"):
                await log.emit(UserLogin(user_id=5, ip="x"))

        asyncio.run(run())
        assert sink.records[0].context["job_id"] == "batch-001"
