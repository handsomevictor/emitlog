# TESTING.md — Test Suite Reference

## How to Run Tests Locally

### Prerequisites

Install development dependencies (includes pytest, pytest-asyncio, mypy, etc.):

```bash
uv sync --extra dev
```

### Run All Tests

```bash
uv run pytest tests/ -v
```

### Useful Flags

```bash
# Short traceback on failure (recommended for daily use)
uv run pytest tests/ -v --tb=short

# Run a single test file
uv run pytest tests/test_span.py -v

# Run a single test by name
uv run pytest tests/test_context.py::TestContextAsync::test_context_isolation_in_gather -v

# Run all tests matching a keyword
uv run pytest tests/ -v -k "color"

# Stop on first failure
uv run pytest tests/ -x

# Show print() output (useful for debugging)
uv run pytest tests/ -v -s

# Run type checking (not pytest, but run it alongside tests)
uv run mypy emitlog --strict
```

### Expected Output

All 119 tests should pass with zero warnings:

```
============================= 119 passed in 0.32s ==============================
```

---

## Test File Reference

### `conftest.py` — Shared Fixtures

Contains one `autouse=True` fixture that runs after **every** test:

- **`reset_emitlog_config`** — Resets global emitlog config to defaults and sets root stdlib logger back to `WARNING`. Prevents state from one test leaking into the next (especially important when `capture_stdlib=True` is used, which would otherwise flood subsequent tests with asyncio debug messages).

---

### `test_span.py` — Inline Color Spans

Tests for `Span`, `SpanList`, `colored()`, `span()`, `markup()` in `_span.py`.

**`TestSpan`**

| Test | What it checks |
|---|---|
| `test_colored_returns_span` | `colored("x", "red")` returns a `Span` instance |
| `test_str_gives_plain_text` | `str(span)` returns the raw text with no ANSI codes |
| `test_repr` | `repr(span)` returns `Span('x', 'red')` |
| `test_len` | `len(span)` returns the length of the plain text |
| `test_span_alias` | `span()` is an exact alias for `colored()` |
| `test_span_plus_span_returns_spanlist` | `Span + Span` produces a `SpanList` |
| `test_span_plus_str_returns_spanlist` | `Span + str` produces a `SpanList`; the `str` is treated as a colorless span |
| `test_str_plus_span_radd` | `str + Span` works via `__radd__`, returns `SpanList` |
| `test_span_plus_spanlist` | `Span + SpanList` appends the span to the list |
| `test_equality` | Two `Span` objects with same text and color are equal |

**`TestSpanList`**

| Test | What it checks |
|---|---|
| `test_str_returns_plain_text` | `str(spanlist)` concatenates all spans as plain text |
| `test_len_returns_plain_text_length` | `len(spanlist)` sums the plain-text length of all spans |
| `test_spanlist_plus_span` | `SpanList + Span` appends the span |
| `test_spanlist_plus_str` | `SpanList + str` appends a colorless span |
| `test_spanlist_plus_spanlist` | `SpanList + SpanList` merges the two lists |
| `test_str_radd_spanlist` | `str + SpanList` prepends a colorless span via `__radd__` |

**`TestMarkup`**

| Test | What it checks |
|---|---|
| `test_basic_color_tag` | `[red]text[/red]` parses into a `Span` with color `"red"` |
| `test_plain_text` | Text with no tags returns a `SpanList` with one colorless span |
| `test_multiple_tags` | Multiple sibling tags each become their own `Span` |
| `test_nested_tags` | Nested tags like `[bold][red]x[/red][/bold]` parse correctly |
| `test_unknown_color_no_error` | Unknown tag names do not raise — treated as colorless |
| `test_unbalanced_tags_no_error` | Unclosed opening tags do not raise |
| `test_unbalanced_close_no_error` | Orphan closing tags do not raise |
| `test_complex_markup` | Mixed known/unknown tags in a single string |
| `test_empty_string` | `markup("")` returns an empty `SpanList` |
| `test_mixed_colored_and_plain` | Text with both tagged and untagged sections |

---

### `test_context.py` — Context Propagation

Tests for `_ContextManager` and `get_current_context()` in `_context.py`.

**`TestContextSync`**

| Test | What it checks |
|---|---|
| `test_single_layer_context_injected` | Fields passed to `with log.context(...)` appear in `get_current_context()` |
| `test_context_restored_after_exit` | After the `with` block exits, all fields are gone |
| `test_nested_inner_overrides_outer` | Inner context overrides outer fields with the same key |
| `test_nested_outer_restored_after_inner_exit` | After inner block exits, outer value is correctly restored |
| `test_exception_restores_context` | An exception inside the block still restores context on exit |
| `test_sync_context_manager_works` | `with` (sync) form works correctly |

**`TestContextAsync`**

| Test | What it checks |
|---|---|
| `test_async_single_layer` | `async with log.context(...)` injects fields |
| `test_async_nested` | Nested `async with` blocks nest and restore correctly |
| `test_async_exception_restores` | Exception inside `async with` block still restores context |
| `test_context_isolation_in_gather` | **Critical boundary case**: two coroutines running via `asyncio.gather` each maintain fully independent context — no cross-contamination |

---

### `test_event.py` — @event Decorator and field()

Tests for `@event`, `field()`, and validation in `_event.py`.

| Test | What it checks |
|---|---|
| `test_decorated_class_is_dataclass` | `@event` results in a valid `dataclass` (passes `dataclasses.is_dataclass()`) |
| `test_instantiation_works` | Decorated class can be instantiated with positional and keyword args |
| `test_missing_required_field_raises_typeerror` | Missing a required field raises `TypeError` at instantiation (standard dataclass behavior) |
| `test_sample_by_nonexistent_field_raises_valueerror` | `sample_by="nonexistent"` raises `ValueError` **at decoration time**, not at emit time |
| `test_field_color_and_color_map_raises_valueerror` | Specifying both `color=` and `color_map=` on the same field raises `ValueError` at decoration time |
| `test_color_map_range_matching` | Values in different ranges map to the correct color strings |
| `test_event_name_snake_case` | `UserLogin` → `"user_login"` |
| `test_event_name_complex_snake_case` | `HTTPRequestLog` → `"http_request_log"` |
| `test_metadata_attributes_set` | `__emitlog_level__`, `__emitlog_sample_rate__`, `__emitlog_event_name__` are set on the class |
| `test_field_with_color_metadata` | `field(color="cyan")` stores color metadata accessible via `__emitlog_field_meta__` |
| `test_field_with_color_map` | `field(color_map=[...])` stores color map metadata correctly |
| `test_sample_rate_default_is_1` | Default `sample_rate` is `1.0` |
| `test_health_check_with_sample_rate` | `sample_rate=0.01` is stored correctly |
| `test_emit_non_event_raises_typeerror` | Passing a non-`@event` instance to `emit()` raises `TypeError` |

---

### `test_sampling.py` — Sampling Logic

Tests for `should_emit()` in `_sampling.py`.

| Test | What it checks |
|---|---|
| `test_rate_1_always_emits` | `sample_rate=1.0` — all 1000 calls return `True` |
| `test_rate_0_drops_all` | `sample_rate=0.0` — all 1000 calls return `False` |
| `test_sample_by_same_value_idempotent` | Same `sample_by` value always returns the same decision across 100 calls |
| `test_sample_by_different_values_distributed` | 1000 different values at `sample_rate=0.5` — result is within ±5% of 50% |
| `test_sample_by_100_percent_all_pass` | `sample_by` with `sample_rate=1.0` — all pass |
| `test_sample_by_0_percent_all_drop` | `sample_by` with `sample_rate=0.0` — all drop |
| `test_sample_by_consistency_across_calls` | Same field value → same decision, verified deterministically |
| `test_no_sample_by_is_random` | Without `sample_by`, sampling is random with correct distribution |

---

### `test_serializer.py` — JSON Serialization

Tests for `serialize()` in `_serializer.py`.

| Test | What it checks |
|---|---|
| `test_returns_valid_json` | Output is parseable JSON |
| `test_field_order` | Key order is: `timestamp → level → logger_name → event_name → fields → context` |
| `test_fields_before_context` | Event fields appear before context fields in output |
| `test_basic_values` | Strings, ints, and floats serialize correctly |
| `test_empty_fields_and_context` | Empty `fields` and `context` dicts produce clean JSON |
| `test_non_serializable_uses_str` | Non-JSON-serializable values (e.g. custom objects) fall back to `str()` |
| `test_unicode_values` | Unicode characters serialize correctly |

---

### `test_formatters.py` — PrettyFormatter and JsonFormatter

Tests for all formatters in `formatters/`.

**`TestPrettyFormatter`**

| Test | What it checks |
|---|---|
| `test_output_contains_all_fields` | Formatted string contains all event field keys and values |
| `test_output_contains_timestamp` | Timestamp appears in output |
| `test_output_contains_level` | Log level appears in output |
| `test_colorize_false_no_ansi` | `colorize=False` produces zero ANSI escape codes (`\033[`) |
| `test_colorize_true_has_ansi` | `colorize=True` produces ANSI escape codes |
| `test_no_color_env_disables_colors` | `NO_COLOR=1` env var removes all ANSI codes regardless of `colorize` setting |
| `test_emitlog_no_color_env_disables_colors` | `EMITLOG_NO_COLOR=1` env var also removes ANSI codes |
| `test_span_field_rendered_with_color` | A `Span` field is rendered with its ANSI color in the output |
| `test_span_field_plain_when_no_color` | With `colorize=False`, a `Span` field renders as plain text |
| `test_spanlist_field_rendered` | A `SpanList` field is rendered with each span's ANSI color |
| `test_color_map_applies_correct_color` | A field with `color_map` applies the correct color for the given value |
| `test_custom_color_scheme` | A custom `ColorScheme` changes the colors used in output |
| `test_context_separator_shown` | `show_context_separator=True` includes `│` between fields and context |
| `test_context_separator_hidden` | `show_context_separator=False` omits the separator |
| `test_value_only_field_style` | `field_style="value_only"` omits the `key=` prefix |

**`TestJsonFormatter`**

| Test | What it checks |
|---|---|
| `test_returns_valid_json` | Output is parseable JSON |
| `test_span_field_as_plain_text` | A `Span` field appears as plain text string in JSON (no ANSI) |
| `test_spanlist_as_plain_text` | A `SpanList` field appears as concatenated plain text in JSON |
| `test_no_ansi_in_output` | JSON output contains no ANSI escape codes |
| `test_field_order` | JSON keys follow the specified order |

---

### `test_sinks.py` — Sinks

Tests for `Stderr`, `File`, `AsyncFile`, and custom sink in `sinks/`.

**`TestStderr`**

| Test | What it checks |
|---|---|
| `test_writes_to_stderr` | Output appears on stderr (captured with `capsys`) |
| `test_close_is_noop` | `await sink.close()` does not raise |
| `test_pretty_formatter_used_in_dev_mode` | `EMITLOG_DEV=1` env var causes `PrettyFormatter` to be selected automatically |
| `test_custom_formatter` | A custom formatter passed to `Stderr()` is used |

**`TestFile`**

| Test | What it checks |
|---|---|
| `test_writes_to_file` | Output is written to the file and is valid JSON |
| `test_appends_to_file` | Multiple writes append lines; file has correct line count |
| `test_custom_formatter` | A custom formatter passed to `File()` is used |
| `test_default_json_formatter` | Without a formatter, `File` defaults to `JsonFormatter` |

**`TestAsyncFile`**

| Test | What it checks |
|---|---|
| `test_writes_to_file` | After `close()`, output is flushed and written |
| `test_lazy_start` | Background task does **not** start in `__init__` — only starts on first `write()` |
| `test_multiple_records` | Multiple records all appear in the file after `close()` |
| `test_drop_overflow_policy` | With `overflow_policy="drop"` and a full queue, extra records are silently dropped (no error) |

**`TestCustomSink`**

| Test | What it checks |
|---|---|
| `test_custom_sink_can_serialize` | A subclass of `BaseSink` can call `self._serialize(record)` and receive a valid JSON string |

---

### `test_logger.py` — Logger

Tests for `get_logger()`, `emit()`, `emit_sync()`, and `context()` in `_logger.py`.

**`TestGetLogger`**

| Test | What it checks |
|---|---|
| `test_returns_logger` | `get_logger("name")` returns a `Logger` instance |
| `test_same_name_same_instance` | Calling `get_logger` twice with the same name returns the same object |

**`TestEmit`**

| Test | What it checks |
|---|---|
| `test_emit_event_works` | Emitting a valid `@event` instance produces a `LogRecord` in the sink |
| `test_emit_non_event_raises_typeerror` | Emitting a plain class instance raises `TypeError` |
| `test_level_filtering` | Records below the configured level are dropped |
| `test_sampling_zero_drops_all` | `sample_rate=0.0` event is never written to the sink |
| `test_context_injected` | Fields set in `log.context()` appear in `record.context` |
| `test_nested_context` | Nested contexts merge and restore correctly in emitted records |
| `test_span_field_plain_in_fields` | `record.fields` contains plain text; `record.raw_fields` contains the original `Span` |
| `test_logger_name_in_record` | `record.logger_name` matches the name passed to `get_logger()` |
| `test_timestamp_format` | `record.timestamp` matches ISO 8601 UTC format with milliseconds |
| `test_gather_context_isolation` | Two coroutines in `asyncio.gather` produce records with their own independent context |

**`TestEmitSync`**

| Test | What it checks |
|---|---|
| `test_emit_sync_works` | `log.emit_sync(...)` works outside of an async context |
| `test_emit_sync_in_async_raises` | `log.emit_sync(...)` called inside a coroutine raises `RuntimeError` with a helpful message |

**`TestContextManager`**

| Test | What it checks |
|---|---|
| `test_sync_context_works` | `with log.context(...)` correctly injects and restores fields in sync code |

---

### `test_compat.py` — Stdlib Compatibility

Tests for `_EmitlogHandler` in `_compat.py`.

| Test | What it checks |
|---|---|
| `test_capture_stdlib_true_registers_handler` | `capture_stdlib=True` routes stdlib `logging` calls through emitlog sinks |
| `test_capture_stdlib_false_no_handler` | `capture_stdlib=False` does not install the handler |
| `test_stdlib_log_event_name` | Bridged records always have `event_name="stdlib_log"` |
| `test_emitlog_own_logs_not_captured` | emitlog's own internal logger is not re-captured (prevents infinite loop) |
| `test_reconfigure_removes_old_handler` | Calling `configure()` again removes the previous stdlib handler cleanly |
| `test_warning_level_mapped_correctly` | stdlib `WARNING` level maps to `"warning"` in emitlog (not `"warn"`) |
