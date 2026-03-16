"""Tests for _serializer.py."""

from __future__ import annotations

import json

import pytest

from emitlog._record import LogRecord
from emitlog._serializer import serialize


def make_record(**kwargs: object) -> LogRecord:
    defaults = dict(
        timestamp="2024-01-15T10:23:45.123Z",
        level="info",
        logger_name="myapp",
        event_name="user_login",
        fields={"user_id": 123, "ip": "1.2.3.4"},
        raw_fields={"user_id": 123, "ip": "1.2.3.4"},
        context={"request_id": "abc"},
    )
    defaults.update(kwargs)  # type: ignore[arg-type]
    return LogRecord(**defaults)  # type: ignore[arg-type]


class TestSerialize:
    def test_returns_valid_json(self) -> None:
        record = make_record()
        output = serialize(record)
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_field_order(self) -> None:
        record = make_record()
        output = serialize(record)
        data = json.loads(output)
        keys = list(data.keys())
        assert keys[0] == "timestamp"
        assert keys[1] == "level"
        assert keys[2] == "logger_name"
        assert keys[3] == "event_name"

    def test_fields_before_context(self) -> None:
        record = make_record(
            fields={"user_id": 123},
            raw_fields={"user_id": 123},
            context={"request_id": "abc"},
        )
        output = serialize(record)
        data = json.loads(output)
        keys = list(data.keys())
        user_id_idx = keys.index("user_id")
        request_id_idx = keys.index("request_id")
        assert user_id_idx < request_id_idx

    def test_basic_values(self) -> None:
        record = make_record()
        output = serialize(record)
        data = json.loads(output)
        assert data["timestamp"] == "2024-01-15T10:23:45.123Z"
        assert data["level"] == "info"
        assert data["logger_name"] == "myapp"
        assert data["event_name"] == "user_login"
        assert data["user_id"] == 123
        assert data["ip"] == "1.2.3.4"
        assert data["request_id"] == "abc"

    def test_empty_fields_and_context(self) -> None:
        record = make_record(fields={}, raw_fields={}, context={})
        output = serialize(record)
        data = json.loads(output)
        assert len(data) == 4  # just the 4 base fields

    def test_non_serializable_uses_str(self) -> None:
        class Custom:
            def __str__(self) -> str:
                return "custom_value"

        record = make_record(
            fields={"thing": Custom()},
            raw_fields={"thing": Custom()},
        )
        output = serialize(record)
        data = json.loads(output)
        assert data["thing"] == "custom_value"

    def test_unicode_values(self) -> None:
        record = make_record(
            fields={"msg": "こんにちは"},
            raw_fields={"msg": "こんにちは"},
        )
        output = serialize(record)
        data = json.loads(output)
        assert data["msg"] == "こんにちは"
