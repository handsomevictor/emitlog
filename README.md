# emitlog

> asyncio-first · type-safe · structured logging for Python microservices

[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)
[![mypy: strict](https://img.shields.io/badge/mypy-strict-brightgreen.svg)](https://mypy.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)]()

**emitlog** is a structured logging library built from the ground up for modern async Python. Instead of free-form strings, you define log events as typed dataclasses. Your IDE, your type checker, and your on-call engineer will thank you.

```
10:23:45.123  INFO  api  user_login  user_id=42  ip=192.168.1.1  │  request_id=req-abc  service=api
```

[中文文档 →](README_CN.md)

---

## Why emitlog?

Most Python logging libraries were designed for synchronous, single-threaded code. When you put them in asyncio microservices you hit the same walls:

| Problem | What you're stuck with today |
|---|---|
| Log schema changes silently break dashboards | `logger.info("user %s logged in", user_id)` — the string is the schema |
| `request_id` disappears mid-async-task | `threading.local` doesn't cross coroutine boundaries |
| mypy can't verify your log calls | Every logger call is `Any` |
| Terminal output is unreadable at high velocity | All fields look the same — no visual hierarchy |
| Sampling is bolted on as an afterthought | Filter lambdas run after serialization |

emitlog is designed to eliminate all of these.

---

## Comparison

| Feature | stdlib logging | loguru | structlog | **emitlog** |
|---|---|---|---|---|
| Structured / JSON output | ⚠️ via handler | ✅ | ✅ | ✅ |
| Schema-enforced events | ❌ | ❌ | ❌ | ✅ |
| mypy `--strict` compatible | ❌ | ❌ | ⚠️ partial | ✅ |
| asyncio-native `await emit()` | ❌ | ❌ | ❌ | ✅ |
| `contextvars` propagation | ❌ | ❌ | ⚠️ manual | ✅ built-in |
| `asyncio.gather` context isolation | ❌ | ❌ | ❌ | ✅ automatic |
| Per-field terminal colors | ❌ | ❌ | ❌ | ✅ |
| Value-range color maps | ❌ | ❌ | ❌ | ✅ |
| Inline character-span coloring | ❌ | ❌ | ❌ | ✅ |
| Built-in sampling | ❌ | ❌ | ⚠️ plugin | ✅ |
| Deterministic per-entity sampling | ❌ | ❌ | ❌ | ✅ |
| Zero mandatory dependencies | ✅ | ✅ | ❌ | ✅ |

---

## Installation

```bash
# Core (zero dependencies)
pip install emitlog

# With faster JSON serialization (orjson, ~3–5× faster)
pip install emitlog[fast]

# With rich terminal rendering
pip install emitlog[dev]
```

**Requirements:** Python 3.13+

---

## Quick Start

```python
import asyncio
import emitlog
from emitlog import event

# 1. Define your log event as a typed schema
@event(level="info")
class UserLogin:
    user_id: int
    ip: str

# 2. Get a logger (safe to call at import time — no IO)
log = emitlog.get_logger(__name__)

async def main():
    # 3. Emit — fully typed, mypy-verified
    await log.emit(UserLogin(user_id=42, ip="1.2.3.4"))

asyncio.run(main())
# Output (terminal):
# 10:23:45.123  INFO  __main__  user_login  user_id=42  ip=1.2.3.4
#
# Output (non-tty / production):
# {"timestamp":"2024-01-15T10:23:45.123Z","level":"info","logger_name":"__main__","event_name":"user_login","user_id":42,"ip":"1.2.3.4"}
```

Zero configuration required. emitlog automatically selects colored terminal output when running in a tty, and JSON when piped or running in production.

---

## Core Concepts

### Schema Events

Define events as classes. Fields are validated by the type checker. Rename a field and every call site breaks at `mypy` time, not at 3 AM when your dashboard goes blank.

```python
from emitlog import event, field

@event(level="info")
class OrderCreated:
    order_id: str
    amount: float
    status: str = "pending"   # default values work normally

@event(level="warning")
class RateLimitExceeded:
    user_id: int
    requests_per_minute: int

# Usage — it's a regular dataclass
await log.emit(OrderCreated(order_id="ord-123", amount=99.99))
await log.emit(OrderCreated(order_id="ord-456", amount=1500.0, status="paid"))
```

### Context Propagation

Attach fields to every log record emitted within a block. Built on `contextvars` — each `asyncio` task inherits context independently, so `gather()` tasks can never cross-contaminate each other.

```python
async def handle_request(request_id: str):
    async with log.context(request_id=request_id, service="api"):
        await log.emit(UserLogin(user_id=1, ip="x"))
        # → context: {"request_id": "...", "service": "api"}

        async with log.context(service="db"):
            # Inner overrides outer same-name field
            await log.emit(...)
            # → context: {"request_id": "...", "service": "db"}

        # Outer service restored automatically
        await log.emit(...)
        # → context: {"request_id": "...", "service": "api"}

# asyncio.gather: each coroutine has fully isolated context
await asyncio.gather(handle_request("req-1"), handle_request("req-2"))
```

Sync code works too:

```python
with log.context(job_id="batch-001"):
    log.emit_sync(OrderCreated(order_id="x", amount=0.0))
```

### Terminal Coloring (3 Layers)

emitlog lets you add color at three different levels of granularity:

**Layer 1 — Static field color** (the field is always this color)

```python
@event(level="info")
class OrderCreated:
    order_id: str  = field(color="cyan")
    amount:   float = field(color="bold green")
    status:   str  = field(color="yellow")
```

**Layer 2 — Value-range color map** (color depends on the value)

```python
@event(level="info")
class HttpRequest:
    method: str = field(color="bold cyan")
    status_code: int = field(
        color_map=[
            (range(200, 300), "bold green"),
            (range(300, 400), "cyan"),
            (range(400, 500), "bold yellow"),
            (range(500, 600), "bold red"),
        ]
    )
    duration_ms: float = field(
        color_map=[
            (range(0,   100),   "green"),
            (range(100, 500),   "yellow"),
            (range(500, 99999), "bold red"),
        ]
    )
```

**Layer 3 — Inline character spans** (arbitrary coloring inside a string value)

```python
from emitlog import colored, markup

# colored() / span() — programmatic
msg = colored("i", "green") + " " + colored("love", "red") + " " + colored("you", "blue")

# markup() — tag syntax
msg = markup("[bold green]SUCCESS[/bold green] deployed to [bold red]production[/bold red]")

@event(level="info")
class DeployStatus:
    message: str   # declare as str; pass Span/SpanList at runtime

await log.emit(DeployStatus(message=msg))
# Terminal: renders with colors
# JSON:     {"message": "SUCCESS deployed to production"}  ← plain text, no ANSI
```

### Sampling

```python
# Random 1% sampling — check happens before any serialization
@event(level="info", sample_rate=0.01)
class HealthCheckCalled:
    pass

# Deterministic per-user sampling — same user_id always makes the same decision
# Useful for keeping a user's entire trace or dropping it entirely
@event(level="info", sample_rate=0.1, sample_by="user_id")
class ApiCalled:
    user_id: int
    endpoint: str
```

`sample_rate=1.0` (the default) completely skips the sampling code path — zero overhead.

### Configuration

```python
from emitlog.sinks import Stderr, AsyncFile, File
from emitlog.formatters import PrettyFormatter, JsonFormatter, ColorScheme, LevelColors

emitlog.configure(
    sinks=[
        # Colored terminal output
        Stderr(formatter=PrettyFormatter(
            time_format="%H:%M:%S",
            show_context_separator=True,
            colors=ColorScheme(
                levels=LevelColors(info="bold blue", error="bold white on red"),
                event_name="bold yellow",
                timestamp="dim green",
            ),
        )),
        # Async JSON file (background task, non-blocking)
        AsyncFile("app.log", maxsize=10_000, overflow_policy="drop"),
    ],
    level="info",
    capture_stdlib=True,   # bridge stdlib logging.getLogger() to emitlog
)

# configure() is thread-safe and can be called multiple times
# Old sinks are automatically closed before new ones take effect
```

**Formatter auto-selection** (when no formatter is passed to a sink):

| Sink | Condition | Formatter |
|---|---|---|
| `Stderr` | `sys.stdout.isatty()` or `EMITLOG_DEV=1` | `PrettyFormatter` |
| `Stderr` | otherwise | `JsonFormatter` |
| `File` / `AsyncFile` | always | `JsonFormatter` |

**Color disable** (in order of priority):

```bash
NO_COLOR=1           # https://no-color.org — respected by emitlog
EMITLOG_NO_COLOR=1   # emitlog-specific override
# or: PrettyFormatter(colorize=False)
```

### Custom Sinks and Formatters

```python
from emitlog.sinks import BaseSink
from emitlog.formatters import BaseFormatter
from emitlog._record import LogRecord

# Custom sink — send logs anywhere
class DatadogSink(BaseSink):
    async def write(self, record: LogRecord) -> None:
        payload = self._serialize(record)   # JSON string, provided by BaseSink
        await send_to_datadog(payload)

    async def close(self) -> None:
        pass   # flush / cleanup (optional)

# Custom formatter
class CompactFormatter(BaseFormatter):
    def format(self, record: LogRecord) -> str:
        fields = " ".join(f"{k}={v}" for k, v in record.fields.items())
        return f"{record.level.upper()} {record.event_name} {fields}"
```

### stdlib Compatibility

```python
emitlog.configure(sinks=[...], capture_stdlib=True)

# Existing stdlib logging calls automatically appear in emitlog sinks
import logging
logging.getLogger("sqlalchemy").warning("slow query detected")
# → event_name="stdlib_log", fields={"message": "slow query detected", "logger": "sqlalchemy"}
```

---

## LogRecord Schema

Every emitted event produces a `LogRecord`:

```python
@dataclass(frozen=True)
class LogRecord:
    timestamp:  str              # "2024-01-15T10:23:45.123Z"  (ISO 8601 UTC, ms precision)
    level:      str              # "debug" | "info" | "warning" | "error" | "critical"
    logger_name: str
    event_name: str              # class name → snake_case: UserLogin → "user_login"
    fields:     dict[str, Any]  # event fields, Span/SpanList converted to plain text
    raw_fields:  dict[str, Any] # event fields, Span/SpanList preserved (used by PrettyFormatter)
    context:    dict[str, Any]
```

JSON output key order: `timestamp → level → logger_name → event_name → **fields → **context`

---

## Color Reference

```
Basic colors:    black  red  green  yellow  blue  magenta  cyan  white
Bright colors:   bright_black  bright_red  bright_green  bright_yellow
                 bright_blue   bright_magenta  bright_cyan  bright_white
Modifiers:       bold  dim  italic  underline
Background:      on black  on red  on green  on yellow  on blue ...
Combined:        "bold red"   "dim cyan"   "bold white on red"
No color:        ""  or  None
```

---

## Examples

See the [`examples/`](examples/) directory:

| File | What it shows |
|---|---|
| `01_quickstart.py` | Zero-config startup |
| `02_schema_events.py` | `@event`, `field()`, `color_map` |
| `03_context.py` | Context propagation, nesting, `gather` isolation |
| `04_sampling.py` | `sample_rate`, `sample_by` |
| `05_custom_sink.py` | Writing a custom sink |
| `06_fastapi_integration.py` | Middleware injecting `request_id` |
| `07_stdlib_compat.py` | Bridging `logging.getLogger()` |
| `08_colors_and_formatting.py` | All 3 color layers + `ColorScheme` |

Run any example directly:

```bash
uv run python examples/01_quickstart.py
```

---

## Documentation

| Doc | Description |
|---|---|
| [TUTORIAL.md](docs/TUTORIAL.md) | Full feature guide with examples |
| [TUTORIAL_CN.md](docs/TUTORIAL_CN.md) | 中文功能指南 |
| [CLAUDE.md](docs/CLAUDE.md) | Architecture reference (for contributors) |
| [PROGRESS.md](docs/PROGRESS.md) | Design decisions log |

---

## Contributing

```bash
git clone https://github.com/yourname/emitlog
cd emitlog
uv sync --extra dev

uv run pytest tests/ -v
uv run mypy emitlog --strict
```

---

## License

MIT
