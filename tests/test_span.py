"""Tests for _span.py: Span, SpanList, colored(), span(), markup()."""

from __future__ import annotations

import pytest

from emitlog._span import Span, SpanList, colored, markup, span


class TestSpan:
    def test_colored_returns_span(self) -> None:
        s = colored("hello", "green")
        assert isinstance(s, Span)
        assert s.text == "hello"
        assert s.color == "green"

    def test_str_gives_plain_text(self) -> None:
        s = colored("hello", "bold red")
        assert str(s) == "hello"

    def test_repr(self) -> None:
        s = colored("hello", "green")
        assert repr(s) == "Span('hello', 'green')"

    def test_len(self) -> None:
        s = colored("hello", "green")
        assert len(s) == 5

    def test_span_alias(self) -> None:
        s = span("world", "blue")
        assert isinstance(s, Span)
        assert str(s) == "world"

    def test_span_plus_span_returns_spanlist(self) -> None:
        a = colored("hello", "green")
        b = colored("world", "red")
        result = a + b
        assert isinstance(result, SpanList)
        assert len(result.spans) == 2

    def test_span_plus_str_returns_spanlist(self) -> None:
        a = colored("hello", "green")
        result = a + " world"
        assert isinstance(result, SpanList)
        assert str(result) == "hello world"
        # The str part should be a colorless Span
        assert result.spans[1].color is None

    def test_str_plus_span_radd(self) -> None:
        a = colored("world", "green")
        result = "hello " + a
        assert isinstance(result, SpanList)
        assert str(result) == "hello world"
        assert result.spans[0].color is None

    def test_span_plus_spanlist(self) -> None:
        a = colored("a", "green")
        b = colored("b", "red")
        c = colored("c", "blue")
        sl = b + c
        result = a + sl
        assert isinstance(result, SpanList)
        assert len(result.spans) == 3
        assert str(result) == "abc"

    def test_equality(self) -> None:
        a = Span("hello", "green")
        b = Span("hello", "green")
        c = Span("hello", "red")
        assert a == b
        assert a != c


class TestSpanList:
    def test_str_returns_plain_text(self) -> None:
        sl = colored("hello", "green") + " " + colored("world", "red")
        assert str(sl) == "hello world"

    def test_len_returns_plain_text_length(self) -> None:
        sl = colored("hi", "green") + colored(" there", "blue")
        assert len(sl) == 8

    def test_spanlist_plus_span(self) -> None:
        sl = colored("a", "green") + colored("b", "red")
        c = colored("c", "blue")
        result = sl + c
        assert isinstance(result, SpanList)
        assert len(result.spans) == 3

    def test_spanlist_plus_str(self) -> None:
        sl = colored("hello", "green") + colored(" ", None)
        result = sl + "world"
        assert isinstance(result, SpanList)
        assert str(result) == "hello world"

    def test_spanlist_plus_spanlist(self) -> None:
        sl1 = colored("a", "green") + colored("b", "red")
        sl2 = colored("c", "blue") + colored("d", "yellow")
        result = sl1 + sl2
        assert isinstance(result, SpanList)
        assert len(result.spans) == 4
        assert str(result) == "abcd"

    def test_str_radd_spanlist(self) -> None:
        sl = colored("world", "green") + colored("!", "red")
        result = "hello " + sl
        assert isinstance(result, SpanList)
        assert str(result) == "hello world!"


class TestMarkup:
    def test_basic_color_tag(self) -> None:
        result = markup("[green]hello[/green]")
        assert isinstance(result, SpanList)
        assert str(result) == "hello"
        assert result.spans[0].color == "green"

    def test_plain_text(self) -> None:
        result = markup("hello world")
        assert str(result) == "hello world"

    def test_multiple_tags(self) -> None:
        result = markup("[green]i[/green] [red]love[/red] [blue]you[/blue]")
        assert str(result) == "i love you"
        # Find the colored spans
        colored_spans = [s for s in result.spans if s.color is not None]
        assert len(colored_spans) == 3

    def test_nested_tags(self) -> None:
        result = markup("[bold][red]text[/red][/bold]")
        assert str(result) == "text"
        # Should not raise; inner tag color takes precedence in our stack impl
        assert isinstance(result, SpanList)

    def test_unknown_color_no_error(self) -> None:
        # Unknown color names: no error, treat as colorless Span
        result = markup("[unknowncolor]text[/unknowncolor]")
        assert str(result) == "text"
        assert isinstance(result, SpanList)

    def test_unbalanced_tags_no_error(self) -> None:
        # Unbalanced tags: no error, treat as plain text behavior
        result = markup("[green]unclosed text")
        assert str(result) == "unclosed text"
        assert isinstance(result, SpanList)

    def test_unbalanced_close_no_error(self) -> None:
        result = markup("text[/green]more")
        assert str(result) == "textmore"
        assert isinstance(result, SpanList)

    def test_complex_markup(self) -> None:
        result = markup("[bold green]SUCCESS[/bold green] deployed to [bold red]production[/bold red]")
        assert str(result) == "SUCCESS deployed to production"

    def test_empty_string(self) -> None:
        result = markup("")
        assert isinstance(result, SpanList)
        assert str(result) == ""

    def test_mixed_colored_and_plain(self) -> None:
        result = markup("prefix [green]colored[/green] suffix")
        assert str(result) == "prefix colored suffix"
        # Find plain spans
        plain_spans = [s for s in result.spans if s.color is None]
        assert len(plain_spans) >= 1
