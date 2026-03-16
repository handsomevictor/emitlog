"""Inline span coloring API: colored(), span(), markup(), Span, SpanList."""

from __future__ import annotations

import re
from typing import Union

__all__ = ["Span", "SpanList", "colored", "span", "markup"]


class Span:
    """A piece of text with an optional color annotation.

    ``str(span_obj)`` returns plain text; rendering to ANSI codes happens in
    the formatter layer.
    """

    __slots__ = ("text", "color")

    def __init__(self, text: str, color: str | None = None) -> None:
        self.text = text
        self.color = color

    def __str__(self) -> str:
        return self.text

    def __repr__(self) -> str:
        return f"Span({self.text!r}, {self.color!r})"

    def __len__(self) -> int:
        return len(self.text)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Span):
            return self.text == other.text and self.color == other.color
        return NotImplemented

    def __add__(self, other: Union[str, "Span", "SpanList"]) -> "SpanList":
        if isinstance(other, str):
            return SpanList([self, Span(other)])
        if isinstance(other, Span):
            return SpanList([self, other])
        if isinstance(other, SpanList):
            return SpanList([self, *other.spans])
        raise TypeError(f"unsupported operand type(s) for +: 'Span' and {type(other)!r}")

    def __radd__(self, other: object) -> "SpanList":
        if isinstance(other, str):
            return SpanList([Span(other), self])
        raise TypeError(f"unsupported operand type(s) for +: {type(other)!r} and 'Span'")


class SpanList:
    """An ordered collection of ``Span`` objects that behaves like a string."""

    __slots__ = ("spans",)

    def __init__(self, spans: list[Span]) -> None:
        self.spans = spans

    def __str__(self) -> str:
        return "".join(s.text for s in self.spans)

    def __repr__(self) -> str:
        return f"SpanList({self.spans!r})"

    def __len__(self) -> int:
        return sum(len(s) for s in self.spans)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SpanList):
            return self.spans == other.spans
        return NotImplemented

    def __add__(self, other: Union[str, Span, "SpanList"]) -> "SpanList":
        if isinstance(other, str):
            return SpanList([*self.spans, Span(other)])
        if isinstance(other, Span):
            return SpanList([*self.spans, other])
        if isinstance(other, SpanList):
            return SpanList([*self.spans, *other.spans])
        raise TypeError(f"unsupported operand type(s) for +: 'SpanList' and {type(other)!r}")

    def __radd__(self, other: object) -> "SpanList":
        if isinstance(other, str):
            return SpanList([Span(other), *self.spans])
        raise TypeError(f"unsupported operand type(s) for +: {type(other)!r} and 'SpanList'")


def colored(text: str, color: str) -> Span:
    """Create a ``Span`` with the given color.

    Parameters
    ----------
    text:
        The text content.
    color:
        Color specification, e.g. ``"bold green"`` or ``"bright_red"``.
    """
    return Span(text, color)


def span(text: str, color: str) -> Span:
    """Alias for :func:`colored`."""
    return Span(text, color)


# Regex to match [color]...[/color] or [/color] closing tags
_TAG_RE = re.compile(r"\[(/?)([^\]]*)\]")


def markup(text: str) -> SpanList:
    """Parse a Rich-like markup string into a ``SpanList``.

    Supports ``[color]text[/color]`` syntax with nesting.
    Unknown color names are treated as colorless spans.
    Unbalanced tags are treated as plain text (no exception raised).
    """
    spans: list[Span] = []
    color_stack: list[str] = []
    pos = 0

    for m in _TAG_RE.finditer(text):
        start, end = m.start(), m.end()
        closing, tag_name = m.group(1), m.group(2).strip()

        # Emit any plain text before this tag
        if start > pos:
            plain = text[pos:start]
            current_color = color_stack[-1] if color_stack else None
            spans.append(Span(plain, current_color))

        if closing:
            # Closing tag: pop from stack if it matches the top
            if color_stack and (not tag_name or color_stack[-1] == tag_name):
                color_stack.pop()
            # else: unbalanced closing tag — silently ignore
        else:
            # Opening tag
            color_stack.append(tag_name if tag_name else "")

        pos = end

    # Emit any remaining text after the last tag
    if pos < len(text):
        plain = text[pos:]
        current_color = color_stack[-1] if color_stack else None
        spans.append(Span(plain, current_color))

    # If nothing was parsed, return a single colorless span
    if not spans:
        spans.append(Span("", None))

    return SpanList(spans)
