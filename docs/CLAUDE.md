# CLAUDE.md — emitlog Architecture Reference

## One-line Description

emitlog is an asyncio-first, type-safe, structured logging library for Python microservices with zero mandatory dependencies.

## Core Architecture

```
User code
    │
    ▼
get_logger(name) ──► Logger (no state, reads global config at emit time)
    │
    ▼
@event class instance ──► Logger.emit(obj)
    │
    ├── Level filter (GlobalConfig.level_enabled)
    ├── Sampling (should_emit: sample_rate + sample_by hash)
    ├── Context snapshot (contextvars._ctx.get())
    ├── Build LogRecord (raw_fields + plain fields)
    │
    ▼
for sink in config.sinks:
    ├── sink.write(record)  ──► Formatter.format(record) ──► output string
    │                              ├── PrettyFormatter: ANSI-colored text
    │                              └── JsonFormatter: JSON via _serializer.py
    └── (file sink: queue ──► background task ──► file)
```

## Key File Responsibilities

| File | Responsibility |
|------|----------------|
| `_record.py` | Immutable `LogRecord` dataclass — the value object that flows through the pipeline |
| `_span.py` | `Span`, `SpanList`, `colored()`, `span()`, `markup()` — inline color API |
| `_serializer.py` | JSON serialization; uses `orjson` when available, stdlib `json` otherwise |
| `_context.py` | `contextvars`-based context propagation; `_ContextManager` for sync/async |
| `_sampling.py` | `should_emit()` — deterministic hash-based or random sampling |
| `_event.py` | `@event` decorator and `field()` — turns classes into typed log events |
| `_config.py` | `_GlobalConfig` singleton, `configure()` with threading.Lock protection |
| `_logger.py` | `Logger` class — `emit()`, `emit_sync()`, `context()` |
| `_compat.py` | `_EmitlogHandler` — bridges stdlib `logging` module to emitlog sinks |
| `formatters/_ansi.py` | Pure-Python ANSI escape code generation (no external deps) |
| `formatters/_base.py` | `BaseFormatter` abstract class |
| `formatters/_pretty.py` | `PrettyFormatter`, `ColorScheme`, `LevelColors` |
| `formatters/_json.py` | `JsonFormatter` — delegates to `_serializer.py` |
| `sinks/_base.py` | `BaseSink` abstract class with `_serialize()` helper |
| `sinks/_stderr.py` | `Stderr` sink — writes to `sys.stderr` |
| `sinks/_file.py` | `File` (sync) and `AsyncFile` (async queue + background task) |

## Current Status

| Module | Impl | Test | Doc |
|--------|------|------|-----|
| `_record.py` | ✅ | ✅ | ✅ |
| `_span.py` | ✅ | ✅ | ✅ |
| `_serializer.py` | ✅ | ✅ | ✅ |
| `_context.py` | ✅ | ✅ | ✅ |
| `_sampling.py` | ✅ | ✅ | ✅ |
| `_event.py` | ✅ | ✅ | ✅ |
| `formatters/` | ✅ | ✅ | ✅ |
| `sinks/` | ✅ | ✅ | ✅ |
| `_logger.py` | ✅ | ✅ | ✅ |
| `_compat.py` | ✅ | ✅ | ✅ |
| `_config.py` | ✅ | ✅ | ✅ |
| `examples/` | ✅ | ✅ | ✅ |

## Known Issues and Limitations

- `emit_sync()` cannot be called from within a running event loop (raises RuntimeError with helpful message suggesting `await log.emit()`).
- `AsyncFile` background task must be `await sink.close()`'d to flush remaining records.
- `capture_stdlib=True` uses `loop.create_task()` when inside an async context; in pure sync contexts uses `asyncio.run()` which creates a new event loop per log record — not suitable for high-throughput stdlib bridging in sync code.
- `LogRecord` is a frozen dataclass; `_field_meta` is attached via `object.__setattr__` as a workaround to pass formatter metadata without changing the public API.

## Dev Commands Reference

```bash
# Run all tests
uv run pytest tests/ -v --tb=short

# Run type checking
uv run mypy emitlog --strict

# Run specific example
uv run python examples/01_quickstart.py

# Run all examples
uv run python examples/01_quickstart.py
uv run python examples/02_schema_events.py
uv run python examples/03_context.py
uv run python examples/04_sampling.py
uv run python examples/05_custom_sink.py
uv run python examples/06_fastapi_integration.py
uv run python examples/07_stdlib_compat.py
uv run python examples/08_colors_and_formatting.py
```
