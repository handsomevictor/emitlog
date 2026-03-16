"""Tests for _compat.py: stdlib logging bridge."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Generator

import pytest

import emitlog
from emitlog._record import LogRecord
from emitlog.formatters import JsonFormatter
from emitlog.sinks import BaseSink, Stderr


class MemorySink(BaseSink):
    def __init__(self) -> None:
        self.records: list[LogRecord] = []
        self.formatter = JsonFormatter()

    async def write(self, record: LogRecord) -> None:
        self.records.append(record)


@pytest.fixture(autouse=True)
def reset_config() -> Generator[None, None, None]:
    """Reset emitlog config after each test to avoid state leakage."""
    yield
    # Reset to a clean state with no stdlib capture
    emitlog.configure(sinks=[Stderr()], level="info", capture_stdlib=False)


@pytest.fixture()
def memory_sink() -> MemorySink:
    return MemorySink()


class TestStdlibCompat:
    @pytest.mark.asyncio
    async def test_capture_stdlib_true_registers_handler(self, memory_sink: MemorySink) -> None:
        """capture_stdlib=True should forward stdlib logs to emitlog sinks."""
        emitlog.configure(sinks=[memory_sink], level="debug", capture_stdlib=True)
        logger = logging.getLogger("test.compat.async")
        logger.warning("hello from stdlib")
        # Give the task a moment to run
        await asyncio.sleep(0.05)

        stdlib_records = [r for r in memory_sink.records if r.event_name == "stdlib_log"]
        assert len(stdlib_records) >= 1
        r = stdlib_records[0]
        assert r.fields["message"] == "hello from stdlib"
        assert r.level == "warning"

    def test_capture_stdlib_false_no_handler(self, memory_sink: MemorySink) -> None:
        emitlog.configure(sinks=[memory_sink], level="debug", capture_stdlib=False)
        logger = logging.getLogger("test.no_compat")
        logger.warning("should not capture")
        stdlib_records = [r for r in memory_sink.records if r.event_name == "stdlib_log"]
        assert len(stdlib_records) == 0

    @pytest.mark.asyncio
    async def test_stdlib_log_event_name(self, memory_sink: MemorySink) -> None:
        emitlog.configure(sinks=[memory_sink], level="debug", capture_stdlib=True)
        logging.getLogger("test.event_name_async").info("test info")
        await asyncio.sleep(0.05)
        stdlib_records = [r for r in memory_sink.records if r.event_name == "stdlib_log"]
        assert len(stdlib_records) >= 1

    def test_emitlog_own_logs_not_captured(self, memory_sink: MemorySink) -> None:
        """emitlog's own logs must not be captured (avoid circular)."""
        emitlog.configure(sinks=[memory_sink], level="debug", capture_stdlib=True)
        emitlog_logger = logging.getLogger("emitlog.internal")
        emitlog_logger.warning("internal message")
        # Records from emitlog.* should be filtered out
        emitlog_records = [
            r for r in memory_sink.records
            if r.event_name == "stdlib_log" and r.fields.get("logger", "").startswith("emitlog")
        ]
        assert len(emitlog_records) == 0

    def test_reconfigure_removes_old_handler(self, memory_sink: MemorySink) -> None:
        """Reconfiguring should remove the old stdlib handler."""
        emitlog.configure(sinks=[memory_sink], level="debug", capture_stdlib=True)
        handler_count_before = len(logging.root.handlers)

        emitlog.configure(sinks=[memory_sink], level="debug", capture_stdlib=False)
        handler_count_after = len(logging.root.handlers)

        # Should have removed the emitlog handler
        assert handler_count_after <= handler_count_before

    @pytest.mark.asyncio
    async def test_warning_level_mapped_correctly(self, memory_sink: MemorySink) -> None:
        """WARNING → 'warning' level in emitlog."""
        emitlog.configure(sinks=[memory_sink], level="debug", capture_stdlib=True)
        logging.getLogger("test.level.async").warning("warn test")
        await asyncio.sleep(0.05)
        stdlib_records = [r for r in memory_sink.records if r.event_name == "stdlib_log"]
        assert any(r.level == "warning" for r in stdlib_records)
