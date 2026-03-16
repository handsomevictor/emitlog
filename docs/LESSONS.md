# LESSONS.md — Pitfalls and Solutions

## _span.py

### Problem
`return NotImplemented` in `__add__`/`__radd__` methods causes mypy strict errors.

### Cause
mypy sees the return type as `SpanList` but `NotImplemented` is `NotImplementedType`, not `SpanList`.

### Solution
Raise `TypeError` explicitly instead of returning `NotImplemented`. This is semantically equivalent for our use case since we don't need Python's binary operator fallback mechanism.

### Prevention
When writing dunder methods in mypy strict projects, prefer explicit raises over `return NotImplemented` unless you specifically need the reflective fallback behavior.

---

## _serializer.py

### Problem
Defining `serialize()` function conditionally in `if HAS_ORJSON: ... else: ...` blocks causes `type: ignore[misc]` requirement for the `else` branch.

### Cause
mypy sees the second definition as a re-definition and flags it.

### Solution
Use a single function with a runtime `if` branch. This is cleaner and fully type-safe.

### Prevention
Avoid conditional function definitions for optional-dependency backends. Use runtime branching instead.

---

## _config.py / _compat.py

### Problem
`capture_stdlib=True` sets root logger to `DEBUG`, which causes asyncio internal messages to get captured, creating a feedback loop in tests that ends in `RecursionError`.

### Cause
`asyncio` uses Python's stdlib `logging` at DEBUG level. When emitlog captures stdlib logs, those asyncio debug messages also get captured, which may trigger more asyncio operations, and so on.

### Solution
1. Always reset emitlog config to `capture_stdlib=False` after tests (via autouse fixture in conftest.py).
2. In `_EmitlogHandler.emit()`, filter out `record.name.startswith('emitlog')` to prevent emitlog's own logs from being re-captured.

### Prevention
Test isolation is critical when global state is involved. Always provide autouse teardown fixtures to reset global configuration after tests.

---

## _logger.py

### Problem
`LogRecord` is frozen but `PrettyFormatter` needs per-field metadata (`field_meta`) that isn't part of the public `LogRecord` schema.

### Cause
`@dataclass(frozen=True)` prevents attribute assignment. But if we add `field_meta` to `LogRecord`, it becomes part of the public API and JSON serialization.

### Solution
Attach `_field_meta` via `object.__setattr__(record, "_field_meta", field_meta)` after creation. This bypasses the frozen check. Then `getattr(record, "_field_meta")` retrieves it in the formatter.

### Prevention
When you need to pass side-channel data through a frozen dataclass, consider whether the data belongs in the public API. If not, `object.__setattr__` is a reasonable escape hatch with clear documentation.

---

## sinks/_base.py

### Problem
mypy strict requires `self.formatter` to be declared somewhere, but subclasses set it in `__init__`.

### Cause
`BaseSink._serialize()` uses `self.formatter` but mypy can't find the declaration.

### Solution
Declare `formatter: BaseFormatter | None = None` as a class-level attribute in `BaseSink`. Subclasses override it in `__init__`.

### Prevention
Always declare instance attributes at the class level (or in `__init__`) when using mypy strict. Class-level declarations act as type hints.

---

## examples/06_fastapi_integration.py

### Problem
`httpx.AsyncClient(app=app, base_url="http://test")` raises `TypeError` in newer httpx versions.

### Cause
The `app` parameter was removed from `AsyncClient.__init__` in httpx >= 0.20. You must use `ASGITransport` explicitly.

### Solution
```python
transport = httpx.ASGITransport(app=app)
async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
```

### Prevention
When using httpx for in-process FastAPI testing, always use the `ASGITransport` pattern which is the stable API.
