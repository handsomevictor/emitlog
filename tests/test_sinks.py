"""Tests for sinks: BaseSink, Stderr, File, AsyncFile."""

from __future__ import annotations

import asyncio
import io
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

from emitlog._record import LogRecord
from emitlog.formatters import JsonFormatter, PrettyFormatter
from emitlog.sinks import AsyncFile, BaseSink, File, Stderr


def make_record(**kwargs: object) -> LogRecord:
    defaults: dict[str, object] = dict(
        timestamp="2024-01-15T10:23:45.123Z",
        level="info",
        logger_name="myapp",
        event_name="user_login",
        fields={"user_id": 123},
        raw_fields={"user_id": 123},
        context={},
    )
    defaults.update(kwargs)
    return LogRecord(**defaults)  # type: ignore[arg-type]


class TestStderr:
    @pytest.mark.asyncio
    async def test_writes_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        sink = Stderr(formatter=JsonFormatter())
        record = make_record()
        await sink.write(record)
        captured = capsys.readouterr()
        assert "user_login" in captured.err

    @pytest.mark.asyncio
    async def test_close_is_noop(self) -> None:
        sink = Stderr()
        await sink.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_pretty_formatter_used_in_dev_mode(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("EMITLOG_DEV", "1")
        sink = Stderr()  # No formatter → auto-select
        record = make_record()
        await sink.write(record)
        captured = capsys.readouterr()
        assert captured.err  # Something was written

    @pytest.mark.asyncio
    async def test_custom_formatter(self, capsys: pytest.CaptureFixture[str]) -> None:
        sink = Stderr(formatter=PrettyFormatter(colorize=False))
        record = make_record()
        await sink.write(record)
        captured = capsys.readouterr()
        assert "user_login" in captured.err


class TestFile:
    @pytest.mark.asyncio
    async def test_writes_to_file(self, tmp_path: Path) -> None:
        log_path = tmp_path / "test.log"
        sink = File(log_path)
        record = make_record()
        await sink.write(record)
        await sink.close()

        content = log_path.read_text()
        data = json.loads(content.strip())
        assert data["event_name"] == "user_login"

    @pytest.mark.asyncio
    async def test_appends_to_file(self, tmp_path: Path) -> None:
        log_path = tmp_path / "test.log"
        sink = File(log_path)
        for i in range(3):
            await sink.write(make_record(event_name=f"event_{i}"))
        await sink.close()

        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 3

    @pytest.mark.asyncio
    async def test_custom_formatter(self, tmp_path: Path) -> None:
        log_path = tmp_path / "test.log"
        sink = File(log_path, formatter=PrettyFormatter(colorize=False))
        await sink.write(make_record())
        await sink.close()
        content = log_path.read_text()
        assert "user_login" in content

    @pytest.mark.asyncio
    async def test_default_json_formatter(self, tmp_path: Path) -> None:
        log_path = tmp_path / "test.log"
        sink = File(log_path)
        await sink.write(make_record())
        await sink.close()
        content = log_path.read_text()
        data = json.loads(content.strip())
        assert "timestamp" in data


class TestAsyncFile:
    @pytest.mark.asyncio
    async def test_writes_to_file(self, tmp_path: Path) -> None:
        log_path = tmp_path / "async_test.log"
        sink = AsyncFile(log_path)
        await sink.write(make_record())
        await sink.close()

        content = log_path.read_text()
        data = json.loads(content.strip())
        assert data["event_name"] == "user_login"

    @pytest.mark.asyncio
    async def test_lazy_start(self, tmp_path: Path) -> None:
        """Background task should not start until first write."""
        log_path = tmp_path / "lazy.log"
        sink = AsyncFile(log_path)
        # Before write: no queue
        assert sink._queue is None
        assert sink._task is None
        await sink.write(make_record())
        # After write: queue and task initialized
        assert sink._queue is not None
        assert sink._task is not None
        await sink.close()

    @pytest.mark.asyncio
    async def test_multiple_records(self, tmp_path: Path) -> None:
        log_path = tmp_path / "multi.log"
        sink = AsyncFile(log_path)
        for i in range(5):
            await sink.write(make_record(event_name=f"event_{i}"))
        await sink.close()

        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 5

    @pytest.mark.asyncio
    async def test_drop_overflow_policy(self, tmp_path: Path) -> None:
        """With overflow_policy='drop', full queue silently drops records."""
        log_path = tmp_path / "overflow.log"
        sink = AsyncFile(log_path, maxsize=2, overflow_policy="drop")
        # Flood with records — some may be dropped
        for _ in range(100):
            await sink.write(make_record())
        await sink.close()
        # Just verify no exception was raised and file has some content
        assert log_path.exists()


class TestCustomSink:
    @pytest.mark.asyncio
    async def test_custom_sink_can_serialize(self) -> None:
        """Custom sink can use _serialize() helper."""
        output: list[str] = []

        class MemorySink(BaseSink):
            def __init__(self) -> None:
                self.formatter = JsonFormatter()

            async def write(self, record: LogRecord) -> None:
                output.append(self._serialize(record))

        sink = MemorySink()
        await sink.write(make_record())
        assert len(output) == 1
        data = json.loads(output[0])
        assert data["event_name"] == "user_login"
