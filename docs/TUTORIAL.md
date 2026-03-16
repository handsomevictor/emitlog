# TUTORIAL.md — emitlog Feature Guide

## Zero-Config Startup

emitlog works out of the box with no configuration. It automatically selects `PrettyFormatter` when the terminal is a tty or `EMITLOG_DEV=1` is set, otherwise uses `JsonFormatter`. `get_logger()` is safe to call at import time — it triggers no IO.

```python
import emitlog
from emitlog import event

@event(level="info")
class AppStarted:
    version: str

log = emitlog.get_logger(__name__)

async def main():
    # No configure() call needed — works with defaults
    await log.emit(AppStarted(version="1.0.0"))
```

### Common Errors

- **`TypeError: emit() requires an @event-decorated instance`** — You passed a plain class instance. Decorate it with `@event`.

---

## configure()

`configure()` replaces all sinks and settings. It can be called multiple times. Old sinks are automatically closed.

```python
from emitlog.sinks import Stderr, AsyncFile
from emitlog.formatters import PrettyFormatter, JsonFormatter

emitlog.configure(
    sinks=[
        Stderr(formatter=PrettyFormatter()),
        AsyncFile("app.log"),
    ],
    level="debug",
    capture_stdlib=True,
)
```

### Common Errors

- **`capture_stdlib=True` floods with debug logs** — asyncio logs at DEBUG level. Set `level="info"` or avoid enabling capture_stdlib in tests.

---

## @event Decorator

`@event` turns a class into both a dataclass and a structured log event. It stores metadata (`__emitlog_level__`, `__emitlog_event_name__`, etc.) as class attributes.

```python
from emitlog import event, field

@event(level="info")
class UserLogin:
    user_id: int
    ip: str
    user_agent: str = ""  # default values work normally

# Usage:
obj = UserLogin(user_id=42, ip="1.2.3.4")
# It's a valid dataclass:
import dataclasses
print(dataclasses.asdict(obj))
```

### Common Errors

- **`ValueError: sample_by='nonexistent' is not a field`** — The `sample_by` field name doesn't exist on the class. Check spelling.
- **`ValueError: Field 'x' cannot have both 'color' and 'color_map'`** — Use one or the other, not both.

---

## field()

Extended version of `dataclasses.field()` with color annotations for `PrettyFormatter`.

```python
from emitlog import event, field

@event(level="info")
class HttpRequest:
    method: str = field(color="bold cyan")
    status_code: int = field(
        color_map=[
            (range(200, 300), "bold green"),
            (range(400, 500), "bold yellow"),
            (range(500, 600), "bold red"),
        ]
    )
    duration_ms: float = field(
        color_map=[
            (range(0, 100), "green"),
            (range(100, 500), "yellow"),
            (range(500, 99999), "bold red"),
        ]
    )
```

### Common Errors

- **`ValueError: cannot have both 'color' and 'color_map'`** — These are mutually exclusive. Use `color` for a static color, `color_map` for value-based coloring.

---

## Inline Span Coloring

Three layers of coloring are available. Layer 3 (inline spans) works with `colored()`, `span()`, and `markup()`.

```python
from emitlog import colored, span, markup

# colored() and span() are identical
msg1 = colored("SUCCESS", "bold green") + " deployed"
msg2 = span("ERROR", "bold red") + " something broke"

# markup() parses [color]text[/color] syntax
msg3 = markup("[bold green]SUCCESS[/bold green] to [bold red]prod[/bold red]")

# str(span_obj) returns plain text — safe to use as string
print(str(msg1))  # "SUCCESS deployed"
print(len(msg1))  # 17

# SpanList arithmetic
a = colored("i", "green")
b = colored("love", "red")
c = "you"  # plain string treated as colorless
result = a + " " + b + " " + c  # SpanList
```

### Common Errors

- **`TypeError: unsupported operand`** — You tried to add an unsupported type to a Span. Only `str`, `Span`, and `SpanList` can be combined.
- **Unknown color names in markup()** — Silently treated as colorless. No error is raised.

---

## Context Propagation

Context fields are automatically included in all log records emitted within the context block. Uses `contextvars` so it's safe for `asyncio.gather`.

```python
async with log.context(request_id="abc", service="api"):
    await log.emit(UserLogin(user_id=1, ip="x"))
    # record.context == {"request_id": "abc", "service": "api"}

# Nested contexts: inner overrides outer same-name fields
async with log.context(service="api"):
    async with log.context(service="db"):
        # service == "db" here
    # service == "api" restored here

# asyncio.gather: each coroutine has isolated context
await asyncio.gather(task_a(), task_b())  # no cross-contamination
```

### Common Errors

- **Context not restored after exception** — The context manager always restores context on exit, even on exceptions. This is guaranteed.

---

## Sampling

Sampling decisions happen before serialization for zero overhead at high sample rates.

```python
# 1% random sampling
@event(level="info", sample_rate=0.01)
class HealthCheckCalled:
    pass

# 10% deterministic per-user sampling
# Same user_id always makes the same decision
@event(level="info", sample_rate=0.1, sample_by="user_id")
class ApiCalled:
    user_id: int
    endpoint: str
```

### Common Errors

- **`ValueError: sample_by='x' is not a field`** — Raised at decoration time. Check the field name.

---

## Sinks

### Stderr

Writes to `sys.stderr`. Auto-selects formatter based on tty/`EMITLOG_DEV`.

```python
from emitlog.sinks import Stderr
from emitlog.formatters import PrettyFormatter

sink = Stderr(formatter=PrettyFormatter())
```

### File / AsyncFile

```python
from emitlog.sinks import File, AsyncFile

# Synchronous file (flushes after each write)
sync_sink = File("app.log")

# Async buffered file (background task, queue-based)
async_sink = AsyncFile(
    "app.log",
    maxsize=10_000,
    overflow_policy="drop",  # or "block"
)
# Always close AsyncFile to flush remaining records
await async_sink.close()
```

### Custom Sink

```python
from emitlog.sinks import BaseSink
from emitlog._record import LogRecord

class DatadogSink(BaseSink):
    async def write(self, record: LogRecord) -> None:
        payload = self._serialize(record)  # JSON string
        await send_to_datadog(payload)

    async def close(self) -> None:
        pass  # optional cleanup
```

---

## Formatters

### PrettyFormatter

```python
from emitlog.formatters import PrettyFormatter, ColorScheme, LevelColors

fmt = PrettyFormatter(
    time_format="%H:%M:%S",
    columns=["time", "level", "event", "fields"],
    field_style="key=value",     # or "value_only"
    show_context_separator=True,
    colorize=True,
    force_ansi=False,            # force ANSI even if not tty
    colors=ColorScheme(
        levels=LevelColors(info="bold blue"),
        event_name="bold yellow",
    ),
)
```

Color disable priority: `NO_COLOR=1` > `EMITLOG_NO_COLOR=1` > `colorize=False`.

### JsonFormatter

```python
from emitlog.formatters import JsonFormatter
fmt = JsonFormatter()  # single-line JSON, field order: timestamp → level → logger_name → event_name → fields → context
```

### Custom Formatter

```python
from emitlog.formatters import BaseFormatter
from emitlog._record import LogRecord

class CompactFormatter(BaseFormatter):
    def format(self, record: LogRecord) -> str:
        return f"{record.level.upper()} {record.event_name}"
```

---

## Stdlib Compatibility

```python
emitlog.configure(
    sinks=[...],
    capture_stdlib=True,  # bridges stdlib logging to emitlog
)

import logging
logging.getLogger("myapp").warning("old code still works")
# → appears in emitlog sinks as event_name="stdlib_log"
```

### Common Errors

- **Infinite loop / recursion in tests** — `capture_stdlib=True` + asyncio at DEBUG level creates feedback. Always reset to `capture_stdlib=False` after tests (use teardown fixtures).
