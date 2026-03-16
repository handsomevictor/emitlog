"""Tests for _event.py: @event decorator and field()."""

from __future__ import annotations

import dataclasses

import pytest

from emitlog._event import event, field


class TestEventDecorator:
    def test_decorated_class_is_dataclass(self) -> None:
        @event(level="info")
        class MyEvent:
            x: int
            y: str = "default"

        assert dataclasses.is_dataclass(MyEvent)

    def test_instantiation_works(self) -> None:
        @event(level="info")
        class UserLogin:
            user_id: int
            ip: str
            user_agent: str = ""

        obj = UserLogin(user_id=123, ip="1.2.3.4")
        assert obj.user_id == 123
        assert obj.ip == "1.2.3.4"
        assert obj.user_agent == ""

    def test_missing_required_field_raises_typeerror(self) -> None:
        @event(level="info")
        class RequiredFields:
            x: int
            y: str

        with pytest.raises(TypeError):
            RequiredFields(x=1)  # type: ignore[call-arg]

    def test_sample_by_nonexistent_field_raises_valueerror(self) -> None:
        with pytest.raises(ValueError, match="sample_by"):

            @event(level="info", sample_by="nonexistent")
            class BadEvent:
                user_id: int

    def test_field_color_and_color_map_raises_valueerror(self) -> None:
        with pytest.raises(ValueError, match="color.*color_map|color_map.*color"):

            @event(level="info")
            class BadField:
                value: int = field(color="red", color_map=[(range(0, 10), "green")])

    def test_color_map_range_matching(self) -> None:
        @event(level="info")
        class HttpRequest:
            status_code: int = field(
                color_map=[
                    (range(200, 300), "bold green"),
                    (range(400, 500), "bold yellow"),
                    (range(500, 600), "bold red"),
                ]
            )

        meta = HttpRequest.__emitlog_field_meta__["status_code"]
        color_map = meta["color_map"]
        assert color_map[0][0] == range(200, 300)
        assert color_map[0][1] == "bold green"

    def test_event_name_snake_case(self) -> None:
        @event(level="info")
        class UserLogin:
            user_id: int

        assert UserLogin.__emitlog_event_name__ == "user_login"

    def test_event_name_complex_snake_case(self) -> None:
        @event(level="info")
        class HttpRequestStarted:
            path: str

        assert HttpRequestStarted.__emitlog_event_name__ == "http_request_started"

    def test_metadata_attributes_set(self) -> None:
        @event(level="warning", sample_rate=0.5, sample_by="user_id")
        class TestEvt:
            user_id: int

        assert TestEvt.__emitlog_level__ == "warning"
        assert TestEvt.__emitlog_sample_rate__ == 0.5
        assert TestEvt.__emitlog_sample_by__ == "user_id"

    def test_field_with_color_metadata(self) -> None:
        @event(level="info")
        class OrderCreated:
            order_id: str = field(color="cyan")
            amount: float = field(color="bold green")

        meta = OrderCreated.__emitlog_field_meta__
        assert meta["order_id"]["color"] == "cyan"
        assert meta["amount"]["color"] == "bold green"

    def test_field_with_color_map(self) -> None:
        @event(level="info")
        class Priced:
            amount: float = field(
                color_map=[
                    (range(0, 100), "green"),
                    (range(100, 9999), "bold red"),
                ]
            )

        meta = Priced.__emitlog_field_meta__["amount"]
        assert "color_map" in meta
        assert len(meta["color_map"]) == 2

    def test_sample_rate_default_is_1(self) -> None:
        @event(level="info")
        class Evt:
            x: int

        assert Evt.__emitlog_sample_rate__ == 1.0
        assert Evt.__emitlog_sample_by__ is None

    def test_health_check_with_sample_rate(self) -> None:
        @event(level="info", sample_rate=0.01)
        class HealthCheckCalled:
            pass

        obj = HealthCheckCalled()
        assert obj is not None
        assert HealthCheckCalled.__emitlog_sample_rate__ == 0.01

    def test_emit_non_event_raises_typeerror(self) -> None:
        """emit() must raise TypeError for non-@event instances."""

        class NotAnEvent:
            pass

        obj = NotAnEvent()
        assert not hasattr(obj, "__emitlog_level__")
