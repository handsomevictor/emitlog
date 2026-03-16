# emitlog

为 asyncio 微服务写的 Python 日志库。类型安全，零依赖，开箱即用。

[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)
[![mypy: strict](https://img.shields.io/badge/mypy-strict-brightgreen.svg)](https://mypy.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)]()

```
10:23:45.123  INFO  api  user_login  user_id=42  ip=192.168.1.1  │  request_id=req-abc  service=api
```

[English →](README.md) | [Français →](README_FR.md)

---

## 这是什么

写微服务的时候日志这块其实挺难受的——`logger.info("user %s logged in", user_id)` 这种字符串拼接用多了迟早出问题，改个字段名根本没有任何提示，request_id 在 asyncio task 里一不小心就丢了，采样也得自己手动加。

emitlog 的思路是把日志事件当成 dataclass 来定义，字段类型都是静态声明的，mypy 能检查，IDE 有补全，改错了编译期就报。上下文传播基于 `contextvars`，在 `asyncio.gather` 里跑多个协程也不会串。

核心功能：

- **`@event` 装饰器** — 把普通 class 变成类型化的日志事件
- **上下文传播** — `async with log.context(request_id=...)` 块内所有日志自动带上这些字段，协程间互不干扰
- **三层颜色** — 字段静态颜色、按值范围变色、行内任意片段上色
- **内置采样** — `sample_rate=0.01` 随机采样，或 `sample_by="user_id"` 同一用户始终同一决策
- **零强制依赖** — 纯标准库实现，装了 `orjson` 自动用，不装也行
- **mypy --strict 全覆盖**

---

## 安装

```bash
pip install emitlog

# 想让 JSON 序列化快 3-5 倍，装这个（可选）
pip install emitlog[fast]

# 开发/调试用，带 rich 渲染
pip install emitlog[dev]
```

需要 Python 3.13+。

---

## 快速上手

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
# tty 下输出（带颜色）：
# 10:23:45.123  INFO  __main__  user_login  user_id=42  ip=1.2.3.4
#
# 非 tty / 生产环境自动输出 JSON：
# {"timestamp":"2024-01-15T10:23:45.123Z","level":"info","logger_name":"__main__","event_name":"user_login","user_id":42,"ip":"1.2.3.4"}
```

不用调 `configure()`，在 tty 里就是彩色，重定向到文件或者跑在 k8s 里就是 JSON，自动识别。

---

## 其他库对比

| | stdlib logging | loguru | structlog | emitlog |
|---|---|---|---|---|
| 结构化 / JSON 输出 | ⚠️ 要自己搞 | ✅ | ✅ | ✅ |
| 字段类型约束 | ❌ | ❌ | ❌ | ✅ |
| mypy --strict | ❌ | ❌ | ⚠️ | ✅ |
| asyncio 原生 | ❌ | ❌ | ❌ | ✅ |
| contextvars 上下文 | ❌ | ❌ | ⚠️ 手动 | ✅ |
| gather 协程隔离 | ❌ | ❌ | ❌ | ✅ |
| 字段级终端颜色 | ❌ | ❌ | ❌ | ✅ |
| 内置采样 | ❌ | ❌ | ⚠️ 插件 | ✅ |
| 零依赖 | ✅ | ✅ | ❌ | ✅ |

loguru 写同步脚本很爽，structlog 的 processor pipeline 模式也很灵活，但这两个对 asyncio 的支持都不是原生的，上下文传播得自己搞。emitlog 主要就是针对这块做的。

---

## 主要用法

### 定义事件

```python
from emitlog import event, field

@event(level="info")
class OrderCreated:
    order_id: str
    amount: float
    status: str = "pending"

# 本质上就是个 dataclass，dataclasses.asdict() 之类的都能用
await log.emit(OrderCreated(order_id="ord-123", amount=99.99))
```

### 上下文

```python
async def handle_request(request_id: str):
    async with log.context(request_id=request_id, service="api"):
        await log.emit(UserLogin(user_id=1, ip="x"))
        # 这条日志自动带上 request_id 和 service

        async with log.context(service="db"):
            await log.emit(...)
            # service 变成 "db"，request_id 还在

        # 退出内层后 service 自动恢复成 "api"

# asyncio.gather 里跑多个协程，上下文不会互相污染
await asyncio.gather(handle_request("req-1"), handle_request("req-2"))
```

同步代码也支持：

```python
with log.context(job_id="batch-001"):
    log.emit_sync(OrderCreated(order_id="x", amount=0.0))
```

### 终端颜色

三种粒度，按需选用：

**按字段上色**（这个字段永远这个颜色）

```python
@event(level="info")
class OrderCreated:
    order_id: str  = field(color="cyan")
    amount:   float = field(color="bold green")
    status:   str  = field(color="yellow")
```

**按值范围变色**（比如 HTTP 状态码、响应时间）

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

**行内片段上色**（在一个字符串值里随便上色）

```python
from emitlog import colored, markup

msg = colored("SUCCESS", "bold green") + " deployed to " + colored("prod", "bold red")
msg = markup("[bold green]SUCCESS[/bold green] deployed to [bold red]prod[/bold red]")

# JSON 里自动输出纯文本，不带 ANSI
```

### 采样

```python
# 随机 1% 采样，决策在序列化之前，省 CPU
@event(level="info", sample_rate=0.01)
class HealthCheckCalled:
    pass

# 按 user_id 确定性采样：同一个用户要么全记要么全不记
@event(level="info", sample_rate=0.1, sample_by="user_id")
class ApiCalled:
    user_id: int
    endpoint: str
```

### 配置

```python
from emitlog.sinks import Stderr, AsyncFile
from emitlog.formatters import PrettyFormatter, JsonFormatter, ColorScheme, LevelColors

emitlog.configure(
    sinks=[
        Stderr(formatter=PrettyFormatter(
            colors=ColorScheme(
                levels=LevelColors(info="bold blue", error="bold white on red"),
                event_name="bold yellow",
            ),
        )),
        AsyncFile("app.log"),   # 后台异步写，不阻塞
    ],
    level="info",
    capture_stdlib=True,   # 把老代码里的 logging.getLogger() 也接过来
)
```

不传 formatter 时，Stderr 会自动判断要不要用 PrettyFormatter（看 tty 或 `EMITLOG_DEV=1`），File/AsyncFile 始终用 JSON。

关颜色的几种方式（优先级从高到低）：

```bash
NO_COLOR=1            # 遵循 https://no-color.org
EMITLOG_NO_COLOR=1
# 或者 PrettyFormatter(colorize=False)
```

### 自定义 Sink / Formatter

```python
from emitlog.sinks import BaseSink
from emitlog._record import LogRecord

class DatadogSink(BaseSink):
    async def write(self, record: LogRecord) -> None:
        payload = self._serialize(record)   # BaseSink 提供，返回 JSON 字符串
        await send_to_datadog(payload)
```

```python
from emitlog.formatters import BaseFormatter

class CompactFormatter(BaseFormatter):
    def format(self, record: LogRecord) -> str:
        return f"{record.level.upper()} {record.event_name}"
```

### 接管老的 logging 代码

```python
emitlog.configure(sinks=[...], capture_stdlib=True)

import logging
logging.getLogger("sqlalchemy").warning("slow query")
# 自动变成 event_name="stdlib_log" 出现在 emitlog 的 sink 里
```

---

## LogRecord 结构

```python
@dataclass(frozen=True)
class LogRecord:
    timestamp:   str              # "2024-01-15T10:23:45.123Z"
    level:       str              # "debug" | "info" | "warning" | "error" | "critical"
    logger_name: str
    event_name:  str              # 类名转 snake_case，UserLogin → "user_login"
    fields:      dict[str, Any]  # 事件字段（Span 已转纯文本，给 JSON 用）
    raw_fields:  dict[str, Any]  # 原始字段值（含 Span，给 PrettyFormatter 用）
    context:     dict[str, Any]
```

---

## 颜色速查

```
基础色：  black  red  green  yellow  blue  magenta  cyan  white
亮色：    bright_black  bright_red  bright_green  ...  bright_white
修饰：    bold  dim  italic  underline
背景：    on black  on red  on green  ...  on white
组合：    "bold red"   "dim cyan"   "bold white on red"
```

---

## 示例

```bash
uv run python examples/01_quickstart.py       # 零配置
uv run python examples/02_schema_events.py    # @event + field() + color_map
uv run python examples/03_context.py          # 上下文传播
uv run python examples/04_sampling.py         # 采样
uv run python examples/06_fastapi_integration.py   # FastAPI middleware
uv run python examples/08_colors_and_formatting.py # 三层颜色全演示
```

---

## 文档

- [TUTORIAL_CN.md](docs/TUTORIAL_CN.md) — 详细功能说明
- [TESTING_CN.md](docs/TESTING_CN.md) — 测试说明，怎么在本地跑测试
- [CLAUDE_CN.md](docs/CLAUDE_CN.md) — 架构说明（想参与开发的看这个）

---

## 参与贡献

```bash
git clone https://github.com/handsomevictor/emitlog
cd emitlog
uv sync --extra dev

uv run pytest tests/ -v
uv run mypy emitlog --strict
```

---

MIT License
