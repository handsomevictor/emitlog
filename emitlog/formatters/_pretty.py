"""PrettyFormatter: human-readable colored output for terminals."""

from __future__ import annotations

import dataclasses
from typing import Any

from emitlog._record import LogRecord
from emitlog._span import Span, SpanList
from emitlog.formatters._ansi import ansi_color, should_colorize
from emitlog.formatters._base import BaseFormatter

__all__ = ["PrettyFormatter", "ColorScheme", "LevelColors"]


@dataclasses.dataclass
class LevelColors:
    """Per-level color strings for PrettyFormatter."""

    debug: str = "bright_black"
    info: str = "bold green"
    warning: str = "bold yellow"
    error: str = "bold red"
    critical: str = "bold white on red"


@dataclasses.dataclass
class ColorScheme:
    """Complete color configuration for PrettyFormatter."""

    levels: LevelColors = dataclasses.field(default_factory=LevelColors)
    timestamp: str = "dim"
    logger_name: str = "dim cyan"
    event_name: str = "bold cyan"
    field_key: str = "bright_black"
    field_value: str = "white"
    context_key: str = "dim blue"
    context_value: str = "blue"
    separator: str = "dim"


DEFAULT_COLOR_SCHEME = ColorScheme()

_LEVEL_LABELS: dict[str, str] = {
    "debug": "DEBUG",
    "info": "INFO ",
    "warning": "WARN ",
    "error": "ERROR",
    "critical": "CRIT ",
}


def _color_for_level(level: str, scheme: ColorScheme) -> str:
    return getattr(scheme.levels, level, scheme.levels.info)


class PrettyFormatter(BaseFormatter):
    """Formatter producing human-readable, optionally colorized output.

    Parameters
    ----------
    time_format:
        ``strftime`` format string for the timestamp column.
    columns:
        Ordered list of columns to include.
    field_style:
        ``"key=value"`` (default) or ``"value_only"``.
    field_separator:
        String placed between field pairs.
    show_context_separator:
        If True, insert a ``|`` separator before context fields.
    colorize:
        Enable ANSI coloring (overridden by NO_COLOR / EMITLOG_NO_COLOR).
    colors:
        :class:`ColorScheme` instance.
    force_ansi:
        Force ANSI even if not a tty (useful for tests).
    """

    def __init__(
        self,
        time_format: str = "%H:%M:%S.%f",
        columns: list[str] | None = None,
        field_style: str = "key=value",
        field_separator: str = "  ",
        show_context_separator: bool = True,
        colorize: bool = True,
        colors: ColorScheme | None = None,
        force_ansi: bool = False,
    ) -> None:
        self.time_format = time_format
        self.columns: list[str] = columns if columns is not None else [
            "time", "level", "logger", "event", "fields", "context"
        ]
        self.field_style = field_style
        self.field_separator = field_separator
        self.show_context_separator = show_context_separator
        self.colorize = colorize
        self.colors: ColorScheme = colors if colors is not None else ColorScheme()
        self.force_ansi = force_ansi

    def _use_color(self) -> bool:
        return should_colorize(self.colorize, self.force_ansi)

    def _c(self, text: str, color: str) -> str:
        """Apply color if enabled."""
        if self._use_color() and color:
            return ansi_color(text, color)
        return text

    def _render_span(self, obj: Span | SpanList) -> str:
        """Render a Span or SpanList to a (possibly colored) string."""
        use_color = self._use_color()
        if isinstance(obj, Span):
            spans = [obj]
        else:
            spans = obj.spans
        parts: list[str] = []
        for s in spans:
            if use_color and s.color:
                parts.append(ansi_color(s.text, s.color))
            else:
                parts.append(s.text)
        return "".join(parts)

    def _apply_color_map(
        self,
        value: Any,
        color_map: list[tuple[range | type, str]],
    ) -> str | None:
        """Return the color for ``value`` from ``color_map``, or None."""
        for matcher, color in color_map:
            if isinstance(matcher, range) and isinstance(value, (int, float)):
                if int(value) in matcher:
                    return color
            elif isinstance(matcher, type) and isinstance(value, matcher):
                return color
        return None

    def _format_field_value(
        self,
        key: str,
        raw_value: Any,
        plain_value: Any,
        field_meta: dict[str, Any],
    ) -> str:
        """Format a single field value, applying color as appropriate."""
        use_color = self._use_color()
        meta = field_meta.get(key, {})

        if isinstance(raw_value, (Span, SpanList)):
            return self._render_span(raw_value)

        text = str(plain_value)

        if not use_color:
            return text

        if "color" in meta:
            return self._c(text, meta["color"])
        if "color_map" in meta:
            color = self._apply_color_map(raw_value, meta["color_map"])
            if color:
                return self._c(text, color)
        return self._c(text, self.colors.field_value)

    def format(self, record: LogRecord) -> str:
        """Format a LogRecord as a human-readable line."""
        from datetime import datetime, timezone

        parts: list[str] = []

        # Parse timestamp (stored as ISO string)
        try:
            ts_str = record.timestamp.rstrip("Z")
            dt = datetime.fromisoformat(ts_str).replace(tzinfo=timezone.utc)
            time_str = dt.strftime(self.time_format)
        except Exception:
            time_str = record.timestamp

        use_color = self._use_color()
        level = record.level
        level_label = _LEVEL_LABELS.get(level, level.upper())

        for col in self.columns:
            if col == "time":
                parts.append(self._c(time_str, self.colors.timestamp))
            elif col == "level":
                level_color = _color_for_level(level, self.colors)
                parts.append(self._c(level_label, level_color))
            elif col == "logger":
                parts.append(self._c(record.logger_name, self.colors.logger_name))
            elif col == "event":
                parts.append(self._c(record.event_name, self.colors.event_name))
            elif col == "fields":
                field_parts: list[str] = []
                # Get field_meta from the record's raw_fields extra attr if available
                # We attach it via extra mechanism; fall back to empty dict
                field_meta: dict[str, Any] = {}
                # Try to get field_meta from the record (stored as attribute by logger)
                if hasattr(record, "_field_meta"):
                    field_meta = getattr(record, "_field_meta")

                for k, plain_v in record.fields.items():
                    raw_v = record.raw_fields.get(k, plain_v)
                    formatted_v = self._format_field_value(k, raw_v, plain_v, field_meta)
                    if self.field_style == "key=value":
                        key_str = self._c(f"{k}=", self.colors.field_key)
                        field_parts.append(f"{key_str}{formatted_v}")
                    else:
                        field_parts.append(formatted_v)
                if field_parts:
                    parts.append(self.field_separator.join(field_parts))
            elif col == "context":
                if record.context:
                    ctx_parts: list[str] = []
                    if self.show_context_separator and use_color:
                        ctx_parts.append(self._c("|", self.colors.separator))
                    elif self.show_context_separator:
                        ctx_parts.append("|")
                    for k, v in record.context.items():
                        k_str = self._c(f"{k}=", self.colors.context_key)
                        v_str = self._c(str(v), self.colors.context_value)
                        ctx_parts.append(f"{k_str}{v_str}")
                    parts.append(" ".join(ctx_parts))

        return " ".join(p for p in parts if p)
