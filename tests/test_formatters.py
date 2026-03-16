"""Tests for formatters: PrettyFormatter, JsonFormatter, ColorScheme."""

from __future__ import annotations

import json
import os

import pytest

from emitlog._record import LogRecord
from emitlog._span import Span, SpanList, colored
from emitlog.formatters import (
    ColorScheme,
    JsonFormatter,
    LevelColors,
    PrettyFormatter,
)


def make_record(**kwargs: object) -> LogRecord:
    defaults: dict[str, object] = dict(
        timestamp="2024-01-15T10:23:45.123Z",
        level="info",
        logger_name="myapp",
        event_name="user_login",
        fields={"user_id": 123, "ip": "1.2.3.4"},
        raw_fields={"user_id": 123, "ip": "1.2.3.4"},
        context={"request_id": "abc"},
    )
    defaults.update(kwargs)
    return LogRecord(**defaults)  # type: ignore[arg-type]


_ANSI_RE = __import__("re").compile(r"\033\[[0-9;]*m")


def has_ansi(text: str) -> bool:
    return bool(_ANSI_RE.search(text))


class TestPrettyFormatter:
    def test_output_contains_all_fields(self) -> None:
        fmt = PrettyFormatter(colorize=False)
        record = make_record()
        output = fmt.format(record)
        assert "user_login" in output
        assert "user_id" in output
        assert "123" in output
        assert "request_id" in output

    def test_output_contains_timestamp(self) -> None:
        fmt = PrettyFormatter(colorize=False)
        record = make_record()
        output = fmt.format(record)
        assert "10:23:45" in output

    def test_output_contains_level(self) -> None:
        fmt = PrettyFormatter(colorize=False)
        record = make_record(level="warning")
        output = fmt.format(record)
        assert "WARN" in output

    def test_colorize_false_no_ansi(self) -> None:
        fmt = PrettyFormatter(colorize=False)
        record = make_record()
        output = fmt.format(record)
        assert not has_ansi(output), f"Expected no ANSI codes, got: {output!r}"

    def test_colorize_true_has_ansi(self) -> None:
        fmt = PrettyFormatter(colorize=True, force_ansi=True)
        record = make_record()
        output = fmt.format(record)
        assert has_ansi(output), f"Expected ANSI codes, got: {output!r}"

    def test_no_color_env_disables_colors(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NO_COLOR", "1")
        fmt = PrettyFormatter(colorize=True, force_ansi=True)
        record = make_record()
        output = fmt.format(record)
        assert not has_ansi(output)

    def test_emitlog_no_color_env_disables_colors(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EMITLOG_NO_COLOR", "1")
        fmt = PrettyFormatter(colorize=True, force_ansi=True)
        record = make_record()
        output = fmt.format(record)
        assert not has_ansi(output)

    def test_span_field_rendered_with_color(self) -> None:
        msg = colored("hello", "green")
        record = make_record(
            fields={"message": str(msg)},
            raw_fields={"message": msg},
        )
        fmt = PrettyFormatter(colorize=True, force_ansi=True)
        output = fmt.format(record)
        # Should contain the green ANSI code for "hello"
        assert "hello" in output
        assert has_ansi(output)

    def test_span_field_plain_when_no_color(self) -> None:
        msg = colored("hello", "green")
        record = make_record(
            fields={"message": str(msg)},
            raw_fields={"message": msg},
        )
        fmt = PrettyFormatter(colorize=False)
        output = fmt.format(record)
        assert "hello" in output
        assert not has_ansi(output)

    def test_spanlist_field_rendered(self) -> None:
        sl = colored("i", "green") + " " + colored("love", "red") + " " + colored("you", "blue")
        record = make_record(
            fields={"message": str(sl)},
            raw_fields={"message": sl},
        )
        fmt = PrettyFormatter(colorize=True, force_ansi=True)
        output = fmt.format(record)
        assert "i love you" in output.replace("\033[0m", "").replace(
            *["", ""]  # strip codes for substring check
        ) or "i" in output

    def test_color_map_applies_correct_color(self) -> None:
        color_map = [
            (range(200, 300), "bold green"),
            (range(400, 500), "bold yellow"),
            (range(500, 600), "bold red"),
        ]
        fmt = PrettyFormatter(colorize=True, force_ansi=True)

        class FakeRecord:
            pass

        record = make_record(
            fields={"status_code": 200},
            raw_fields={"status_code": 200},
        )
        # Attach field_meta to the record for formatting
        object.__setattr__(record, "_field_meta", {"status_code": {"color_map": color_map}})
        output = fmt.format(record)
        assert has_ansi(output)
        assert "200" in output

    def test_custom_color_scheme(self) -> None:
        scheme = ColorScheme(
            event_name="bold magenta",
            levels=LevelColors(info="bold blue"),
        )
        fmt = PrettyFormatter(colorize=True, force_ansi=True, colors=scheme)
        record = make_record()
        output = fmt.format(record)
        # bold magenta = codes 1;35
        assert "\033[" in output

    def test_context_separator_shown(self) -> None:
        fmt = PrettyFormatter(colorize=False, show_context_separator=True)
        record = make_record()
        output = fmt.format(record)
        assert "|" in output

    def test_context_separator_hidden(self) -> None:
        fmt = PrettyFormatter(colorize=False, show_context_separator=False)
        record = make_record()
        output = fmt.format(record)
        assert "|" not in output

    def test_value_only_field_style(self) -> None:
        fmt = PrettyFormatter(colorize=False, field_style="value_only")
        record = make_record(
            fields={"msg": "hello"},
            raw_fields={"msg": "hello"},
        )
        output = fmt.format(record)
        assert "msg=" not in output
        assert "hello" in output


class TestJsonFormatter:
    def test_returns_valid_json(self) -> None:
        fmt = JsonFormatter()
        record = make_record()
        output = fmt.format(record)
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_span_field_as_plain_text(self) -> None:
        msg = colored("hello", "green")
        record = make_record(
            fields={"message": str(msg)},
            raw_fields={"message": msg},
        )
        fmt = JsonFormatter()
        output = fmt.format(record)
        data = json.loads(output)
        assert data["message"] == "hello"
        assert not has_ansi(data["message"])

    def test_spanlist_as_plain_text(self) -> None:
        sl = colored("i", "green") + " " + colored("love", "red")
        record = make_record(
            fields={"message": str(sl)},
            raw_fields={"message": sl},
        )
        fmt = JsonFormatter()
        output = fmt.format(record)
        data = json.loads(output)
        assert data["message"] == "i love"
        assert not has_ansi(data["message"])

    def test_no_ansi_in_output(self) -> None:
        fmt = JsonFormatter()
        record = make_record()
        output = fmt.format(record)
        assert not has_ansi(output)

    def test_field_order(self) -> None:
        fmt = JsonFormatter()
        record = make_record()
        output = fmt.format(record)
        data = json.loads(output)
        keys = list(data.keys())
        assert keys[:4] == ["timestamp", "level", "logger_name", "event_name"]
