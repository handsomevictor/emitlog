# PROGRESS.md — emitlog Development Progress

## Status Overview

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
| `docs/` | ✅ | n/a | ✅ |

## Decision Records

### [_record.py] Frozen dataclass
- **Decision:** Use `frozen=True` on `LogRecord`
- **Reason:** Immutability prevents accidental mutation after creation; aligns with the spec
- **Alternatives:** Regular dataclass (mutable, easier for attaching metadata)

### [_span.py] Raise TypeError instead of NotImplemented
- **Decision:** Raise `TypeError` in `__add__`/`__radd__` instead of returning `NotImplemented`
- **Reason:** mypy strict mode rejects `return NotImplemented` when the return type is annotated as `SpanList`
- **Alternatives:** `return NotImplemented` (runtime-correct but mypy can't verify)

### [_serializer.py] Single function with runtime branch
- **Decision:** One `serialize()` function with `if HAS_ORJSON` branch
- **Reason:** Avoids conditional function definition which confuses mypy; cleaner for `--strict`
- **Alternatives:** Two separate function definitions in `if`/`else` blocks (requires `# type: ignore[misc]`)

### [_context.py] Both sync and async context manager in one class
- **Decision:** `_ContextManager` implements both `__enter__`/`__exit__` and `__aenter__`/`__aexit__`
- **Reason:** Allows `with log.context(...)` and `async with log.context(...)` on the same object
- **Alternatives:** Two separate classes (more code, less user-friendly)

### [_event.py] setattr() for class attribute assignment
- **Decision:** Use `setattr(dc, "__emitlog_level__", ...)` instead of `dc.__emitlog_level__ = ...`
- **Reason:** mypy strict mode raises `[attr-defined]` for dynamic attribute assignment on `type`
- **Alternatives:** Protocol class (more complex), dataclasses Protocol (overkill)

### [_logger.py] _field_meta attached via object.__setattr__
- **Decision:** Attach `_field_meta` to the frozen `LogRecord` via `object.__setattr__` then `getattr()`
- **Reason:** `LogRecord` is frozen (spec requirement) but PrettyFormatter needs per-field metadata to apply colors. Passing it in `LogRecord.fields` would pollute the public API.
- **Alternatives:** Add `field_meta` to `LogRecord` directly (changes public API); pass via formatter pre-call (breaks clean separation)

### [sinks/_base.py] formatter as class variable with None default
- **Decision:** Declare `formatter: BaseFormatter | None = None` as class-level attribute
- **Reason:** mypy strict needs `self.formatter` to be declared somewhere accessible to the type checker
- **Alternatives:** Protocol-based approach; TypedDict; passing formatter in `_serialize()` call

### [compat] Tests use async functions for stdlib capture
- **Decision:** Compat tests use `@pytest.mark.asyncio` with `await asyncio.sleep(0.05)` to let tasks run
- **Reason:** `_EmitlogHandler.emit()` is sync but inside an async test loop; it schedules tasks via `loop.create_task()`; we need to yield control for them to execute
- **Alternatives:** Use synchronous event loop manipulation (fragile)

### [conftest.py] Reset config autouse fixture
- **Decision:** Add `autouse=True` fixture that resets emitlog config after every test
- **Reason:** `capture_stdlib=True` sets root logger to DEBUG, which causes asyncio debug messages to flood and create recursion errors in subsequent tests
- **Alternatives:** Per-test teardown (error-prone); module-scoped fixtures (still leaks)

## ✅ ALL DONE
