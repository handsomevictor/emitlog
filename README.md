# emitlog

Structured logging for asyncio Python microservices. Type-safe, zero dependencies, works out of the box.

[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)
[![mypy: strict](https://img.shields.io/badge/mypy-strict-brightgreen.svg)](https://mypy.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)]()

```
10:23:45.123  INFO  api  user_login  user_id=42  ip=192.168.1.1  │  request_id=req-abc  service=api
```

[中文文档 →](README_CN.md) | [Français →](README_FR.md)

---

## Why

Most Python logging libraries were designed before asyncio was a thing. When you use them in async microservices you run into the same problems: log schemas are just strings so renames break silently, `request_id` gets lost when you cross coroutine boundaries because `threading.local` doesn't work there, and mypy has nothing to check because every `logger.info()` call takes `Any`.

emitlog treats log events as typed dataclasses. Fields are statically declared, mypy-checked, and IDE-complete. Context propagation is built on `contextvars`, so it works correctly across `asyncio.gather` without any extra setup.

---

## Comparison

| | stdlib logging | loguru | structlog | emitlog |
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

loguru is great for sync scripts. structlog's processor pipeline is flexible. Neither has native asyncio context propagation — that's the gap emitlog fills.

---

## Installation

```bash
pip install emitlog

# Optional: 3–5× faster JSON serialization
pip install emitlog[fast]

# Optional: rich terminal rendering
pip install emitlog[dev]
```

If PyPI is unavailable, install directly from GitHub:

```bash
pip install "git+https://github.com/handsomevictor/emitlog.git"

# with extras
pip install "git+https://github.com/handsomevictor/emitlog.git#egg=emitlog[fast]"
```

Python 3.13+ required.

---

## Quick Start

```python
import asyncio
import emitlog
from emitlog import event

@event(level="info")
class UserLogin:
    user_id: int
    ip: str

log = emitlog.get_logger(__name__)

async def main():
    await log.emit(UserLogin(user_id=42, ip="1.2.3.4"))

asyncio.run(main())
# Terminal (tty):
# 10:23:45.123  INFO  __main__  user_login  user_id=42  ip=1.2.3.4
#
# Production / non-tty (JSON):
# {"timestamp":"2024-01-15T10:23:45.123Z","level":"info","logger_name":"__main__","event_name":"user_login","user_id":42,"ip":"1.2.3.4"}
```

No configuration needed. emitlog auto-detects tty and picks Pretty or JSON accordingly.

---

## Usage

### Schema Events

```python
from emitlog import event, field

@event(level="info")
class OrderCreated:
    order_id: str
    amount: float
    status: str = "pending"   # defaults work as normal

@event(level="warning")
class RateLimitExceeded:
    user_id: int
    requests_per_minute: int

# It's a regular dataclass — dataclasses.asdict() etc. all work
await log.emit(OrderCreated(order_id="ord-123", amount=99.99))
```

Rename a field and every call site breaks at `mypy` time, not at 3 AM.

### Context Propagation

```python
async def handle_request(request_id: str):
    async with log.context(request_id=request_id, service="api"):
        await log.emit(UserLogin(user_id=1, ip="x"))
        # → context: {"request_id": "...", "service": "api"}

        async with log.context(service="db"):
            await log.emit(...)
            # → context: {"request_id": "...", "service": "db"}

        # outer service automatically restored here

# Works correctly across gather — no cross-contamination
await asyncio.gather(handle_request("req-1"), handle_request("req-2"))
```

Sync version:

```python
with log.context(job_id="batch-001"):
    log.emit_sync(OrderCreated(order_id="x", amount=0.0))
```

### Terminal Coloring (3 layers)

**Layer 1 — static field color**

```python
@event(level="info")
class OrderCreated:
    order_id: str  = field(color="cyan")
    amount:   float = field(color="bold green")
    status:   str  = field(color="yellow")
```

**Layer 2 — value-range color map**

```python
@event(level="info")
class HttpRequest:
    status_code: int = field(
        color_map=[
            (range(200, 300), "bold green"),
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

**Layer 3 — inline character spans**

```python
from emitlog import colored, markup

msg = colored("SUCCESS", "bold green") + " deployed to " + colored("prod", "bold red")
msg = markup("[bold green]SUCCESS[/bold green] deployed to [bold red]prod[/bold red]")

# In JSON output: plain text, no ANSI codes
```

### Sampling

```python
# Random 1% — decision is made before serialization
@event(level="info", sample_rate=0.01)
class HealthCheckCalled:
    pass

# Deterministic per-user — same user_id always gets the same decision
@event(level="info", sample_rate=0.1, sample_by="user_id")
class ApiCalled:
    user_id: int
    endpoint: str
```

`sample_rate=1.0` (the default) skips the sampling code path entirely — no overhead.

### Configuration

```python
from emitlog.sinks import Stderr, AsyncFile
from emitlog.formatters import PrettyFormatter, ColorScheme, LevelColors

emitlog.configure(
    sinks=[
        Stderr(formatter=PrettyFormatter(
            colors=ColorScheme(
                levels=LevelColors(info="bold blue", error="bold white on red"),
                event_name="bold yellow",
            ),
        )),
        AsyncFile("app.log"),   # non-blocking, background task
    ],
    level="info",
    capture_stdlib=True,   # bridge existing logging.getLogger() calls
)
```

Formatter auto-selection when none is specified:

| Sink | Condition | Formatter |
|---|---|---|
| `Stderr` | tty or `EMITLOG_DEV=1` | `PrettyFormatter` |
| `Stderr` | otherwise | `JsonFormatter` |
| `File` / `AsyncFile` | always | `JsonFormatter` |

Disable colors (highest priority first):

```bash
NO_COLOR=1            # https://no-color.org
EMITLOG_NO_COLOR=1
# or: PrettyFormatter(colorize=False)
```

### Custom Sinks and Formatters

```python
from emitlog.sinks import BaseSink
from emitlog._record import LogRecord

class DatadogSink(BaseSink):
    async def write(self, record: LogRecord) -> None:
        payload = self._serialize(record)   # JSON string, from BaseSink
        await send_to_datadog(payload)

    async def close(self) -> None:
        pass
```

```python
from emitlog.formatters import BaseFormatter

class CompactFormatter(BaseFormatter):
    def format(self, record: LogRecord) -> str:
        return f"{record.level.upper()} {record.event_name}"
```

### stdlib Bridge

```python
emitlog.configure(sinks=[...], capture_stdlib=True)

import logging
logging.getLogger("sqlalchemy").warning("slow query")
# → event_name="stdlib_log", fields={"message": "slow query", "logger": "sqlalchemy"}
```

---

## LogRecord

```python
@dataclass(frozen=True)
class LogRecord:
    timestamp:   str              # "2024-01-15T10:23:45.123Z"
    level:       str              # "debug" | "info" | "warning" | "error" | "critical"
    logger_name: str
    event_name:  str              # class name → snake_case: UserLogin → "user_login"
    fields:      dict[str, Any]  # event fields, Span/SpanList as plain text (for JSON)
    raw_fields:  dict[str, Any]  # event fields, Span/SpanList preserved (for PrettyFormatter)
    context:     dict[str, Any]
```

JSON key order: `timestamp → level → logger_name → event_name → **fields → **context`

---

## Color Reference

```
Basic:      black  red  green  yellow  blue  magenta  cyan  white
Bright:     bright_black  bright_red  bright_green  ...  bright_white
Modifiers:  bold  dim  italic  underline
Background: on black  on red  on green  ...  on white
Combined:   "bold red"   "dim cyan"   "bold white on red"
```

---

## Examples

```bash
uv run python examples/01_quickstart.py
uv run python examples/02_schema_events.py
uv run python examples/03_context.py
uv run python examples/04_sampling.py
uv run python examples/06_fastapi_integration.py
uv run python examples/08_colors_and_formatting.py
```

---

## Docs

- [TUTORIAL.md](docs/TUTORIAL.md) — full feature guide
- [TESTING.md](docs/TESTING.md) — running tests locally
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — architecture reference (for contributors)

---

## Contributing

```bash
git clone https://github.com/handsomevictor/emitlog
cd emitlog
uv sync --extra dev

uv run pytest tests/ -v
uv run mypy emitlog --strict
```

---

MIT License
