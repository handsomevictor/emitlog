# emitlog

> asyncio 优先 · 类型安全 · 为 Python 微服务设计的结构化日志库

[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)
[![mypy: strict](https://img.shields.io/badge/mypy-strict-brightgreen.svg)](https://mypy.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)]()

**emitlog** 是一个为现代异步 Python 从零设计的结构化日志库。你不再需要拼接字符串——用类型化 dataclass 定义日志事件，让 IDE、类型检查器和凌晨三点的值班工程师都省心。

```
10:23:45.123  INFO  api  user_login  user_id=42  ip=192.168.1.1  │  request_id=req-abc  service=api
```

[English →](README.md)

---

## 为什么选 emitlog？

大多数 Python 日志库是为同步、单线程代码设计的。用在 asyncio 微服务里，你会撞上同样的墙：

| 痛点 | 现有工具的困境 |
|---|---|
| 日志 schema 悄悄变了，大盘直接炸 | `logger.info("user %s logged in", user_id)` — 字符串就是 schema |
| `request_id` 在 async task 里消失 | `threading.local` 无法跨协程传播 |
| mypy 验证不了日志调用 | 所有 logger 调用参数都是 `Any` |
| 高频日志下终端输出一片混乱 | 所有字段长得一样，没有视觉层次 |
| 采样像个补丁，序列化后才过滤 | 白白浪费了序列化的 CPU |

emitlog 专门解决以上问题。

---

## 竞品对比

| 特性 | stdlib logging | loguru | structlog | **emitlog** |
|---|---|---|---|---|
| 结构化 / JSON 输出 | ⚠️ 需自定义 handler | ✅ | ✅ | ✅ |
| Schema 强制约束 | ❌ | ❌ | ❌ | ✅ |
| mypy `--strict` 兼容 | ❌ | ❌ | ⚠️ 部分 | ✅ |
| asyncio 原生 `await emit()` | ❌ | ❌ | ❌ | ✅ |
| `contextvars` 上下文传播 | ❌ | ❌ | ⚠️ 需手动 | ✅ 内置 |
| `asyncio.gather` 上下文隔离 | ❌ | ❌ | ❌ | ✅ 自动 |
| 字段级终端颜色 | ❌ | ❌ | ❌ | ✅ |
| 按值范围动态上色 | ❌ | ❌ | ❌ | ✅ |
| 行内字符片段上色 | ❌ | ❌ | ❌ | ✅ |
| 内置采样 | ❌ | ❌ | ⚠️ 插件 | ✅ |
| 确定性按实体采样 | ❌ | ❌ | ❌ | ✅ |
| 零强制依赖 | ✅ | ✅ | ❌ | ✅ |

---

## 安装

```bash
# 核心包（零依赖）
pip install emitlog

# 更快的 JSON 序列化（orjson，快 3–5 倍）
pip install emitlog[fast]

# rich 终端渲染后端
pip install emitlog[dev]
```

**运行环境要求：** Python 3.13+

---

## 30 秒快速上手

```python
import asyncio
import emitlog
from emitlog import event

# 1. 定义日志事件（类型化 schema）
@event(level="info")
class UserLogin:
    user_id: int
    ip: str

# 2. 获取 logger（可在 import 阶段调用，不触发任何 IO）
log = emitlog.get_logger(__name__)

async def main():
    # 3. 发送日志——完全类型化，mypy 可验证
    await log.emit(UserLogin(user_id=42, ip="1.2.3.4"))

asyncio.run(main())
# 终端输出（tty）：
# 10:23:45.123  INFO  __main__  user_login  user_id=42  ip=1.2.3.4
#
# 生产环境输出（非 tty）：
# {"timestamp":"2024-01-15T10:23:45.123Z","level":"info","logger_name":"__main__","event_name":"user_login","user_id":42,"ip":"1.2.3.4"}
```

无需任何配置。在 tty 环境自动使用彩色终端输出，在非 tty 或生产环境自动切换为 JSON。

---

## 核心功能

### Schema 事件

用类定义事件。字段由类型检查器验证。重命名一个字段，所有调用处在 `mypy` 时就报错——而不是凌晨三点大盘告警。

```python
from emitlog import event, field

@event(level="info")
class OrderCreated:
    order_id: str
    amount: float
    status: str = "pending"   # 默认值正常工作

@event(level="warning")
class RateLimitExceeded:
    user_id: int
    requests_per_minute: int

# 它是合法的 dataclass
await log.emit(OrderCreated(order_id="ord-123", amount=99.99))
await log.emit(OrderCreated(order_id="ord-456", amount=1500.0, status="paid"))
```

### 上下文传播

在上下文块内发送的所有日志都会自动携带上下文字段。基于 `contextvars` 实现——每个 `asyncio` task 独立继承上下文，`gather()` 中的 task 永远不会互相污染。

```python
async def handle_request(request_id: str):
    async with log.context(request_id=request_id, service="api"):
        await log.emit(UserLogin(user_id=1, ip="x"))
        # → context: {"request_id": "...", "service": "api"}

        async with log.context(service="db"):
            # 内层同名字段覆盖外层
            await log.emit(...)
            # → context: {"request_id": "...", "service": "db"}

        # 退出内层后自动恢复
        await log.emit(...)
        # → context: {"request_id": "...", "service": "api"}

# asyncio.gather：每个协程上下文完全隔离
await asyncio.gather(handle_request("req-1"), handle_request("req-2"))
```

同步代码同样支持：

```python
with log.context(job_id="batch-001"):
    log.emit_sync(OrderCreated(order_id="x", amount=0.0))
```

### 终端颜色（三层体系）

emitlog 支持三种粒度的颜色控制：

**Layer 1 — 字段静态颜色**（该字段始终显示此颜色）

```python
@event(level="info")
class OrderCreated:
    order_id: str   = field(color="cyan")
    amount:   float = field(color="bold green")
    status:   str   = field(color="yellow")
```

**Layer 2 — 按值范围动态上色**（颜色随值变化）

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

**Layer 3 — 行内字符片段上色**（在字符串值内部任意上色）

```python
from emitlog import colored, markup

# colored() / span() — 编程方式
msg = colored("i", "green") + " " + colored("love", "red") + " " + colored("you", "blue")

# markup() — 标签语法
msg = markup("[bold green]SUCCESS[/bold green] 部署到 [bold red]production[/bold red]")

@event(level="info")
class DeployStatus:
    message: str   # 类型声明为 str，运行时可传入 Span/SpanList

await log.emit(DeployStatus(message=msg))
# 终端：带颜色渲染
# JSON：{"message": "SUCCESS 部署到 production"}  ← 纯文本，无 ANSI 码
```

### 采样

```python
# 随机 1% 采样——决策发生在序列化之前
@event(level="info", sample_rate=0.01)
class HealthCheckCalled:
    pass

# 按用户 ID 确定性采样（10%）
# 同一 user_id 始终做出相同决策——要么一直记录，要么一直丢弃
@event(level="info", sample_rate=0.1, sample_by="user_id")
class ApiCalled:
    user_id: int
    endpoint: str
```

`sample_rate=1.0`（默认值）完全跳过采样代码路径——零额外开销。

### 配置

```python
from emitlog.sinks import Stderr, AsyncFile, File
from emitlog.formatters import PrettyFormatter, JsonFormatter, ColorScheme, LevelColors

emitlog.configure(
    sinks=[
        # 彩色终端输出
        Stderr(formatter=PrettyFormatter(
            time_format="%H:%M:%S",
            show_context_separator=True,
            colors=ColorScheme(
                levels=LevelColors(info="bold blue", error="bold white on red"),
                event_name="bold yellow",
                timestamp="dim green",
            ),
        )),
        # 异步 JSON 文件（后台 Task，不阻塞主逻辑）
        AsyncFile("app.log", maxsize=10_000, overflow_policy="drop"),
    ],
    level="info",
    capture_stdlib=True,   # 将 stdlib logging.getLogger() 桥接到 emitlog
)

# configure() 线程安全，可多次调用
# 旧 sink 在新配置生效前自动关闭
```

**Formatter 自动选择**（Sink 未指定 formatter 时）：

| Sink | 条件 | 自动选择 |
|---|---|---|
| `Stderr` | `sys.stdout.isatty()` 或 `EMITLOG_DEV=1` | `PrettyFormatter` |
| `Stderr` | 其他情况 | `JsonFormatter` |
| `File` / `AsyncFile` | 始终 | `JsonFormatter` |

**颜色关闭优先级**（从高到低）：

```bash
NO_COLOR=1           # 遵循 https://no-color.org
EMITLOG_NO_COLOR=1   # emitlog 专用开关
# 或：PrettyFormatter(colorize=False)
```

### 自定义 Sink 和 Formatter

```python
from emitlog.sinks import BaseSink
from emitlog.formatters import BaseFormatter
from emitlog._record import LogRecord

# 自定义 Sink——把日志发送到任何地方
class DatadogSink(BaseSink):
    async def write(self, record: LogRecord) -> None:
        payload = self._serialize(record)   # 由 BaseSink 提供，返回 JSON 字符串
        await send_to_datadog(payload)

    async def close(self) -> None:
        pass   # flush / 清理（可选）

# 自定义 Formatter
class CompactFormatter(BaseFormatter):
    def format(self, record: LogRecord) -> str:
        fields = " ".join(f"{k}={v}" for k, v in record.fields.items())
        return f"{record.level.upper()} {record.event_name} {fields}"
```

### 标准库兼容

```python
emitlog.configure(sinks=[...], capture_stdlib=True)

# 已有的 stdlib logging 调用自动出现在 emitlog sink 中
import logging
logging.getLogger("sqlalchemy").warning("慢查询告警")
# → event_name="stdlib_log", fields={"message": "慢查询告警", "logger": "sqlalchemy"}
```

---

## LogRecord 数据结构

每次 emit 都会产生一个 `LogRecord`：

```python
@dataclass(frozen=True)
class LogRecord:
    timestamp:   str              # "2024-01-15T10:23:45.123Z"（ISO 8601 UTC，毫秒精度）
    level:       str              # "debug" | "info" | "warning" | "error" | "critical"
    logger_name: str
    event_name:  str              # 类名转 snake_case：UserLogin → "user_login"
    fields:      dict[str, Any]  # 事件字段，Span/SpanList 已转纯文本
    raw_fields:  dict[str, Any]  # 事件字段原始值，含 Span/SpanList（PrettyFormatter 使用）
    context:     dict[str, Any]
```

JSON 输出键顺序：`timestamp → level → logger_name → event_name → **fields → **context`

---

## 颜色语法参考

```
基础色：   black  red  green  yellow  blue  magenta  cyan  white
亮色：     bright_black  bright_red  bright_green  bright_yellow
           bright_blue   bright_magenta  bright_cyan  bright_white
修饰符：   bold  dim  italic  underline
背景色：   on black  on red  on green  on yellow  on blue ...
组合：     "bold red"   "dim cyan"   "bold white on red"
无色：     ""  或  None
```

---

## 示例文件

参见 [`examples/`](examples/) 目录：

| 文件 | 演示内容 |
|---|---|
| `01_quickstart.py` | 零配置启动 |
| `02_schema_events.py` | `@event`、`field()`、`color_map` |
| `03_context.py` | 上下文传播、嵌套、`gather` 隔离 |
| `04_sampling.py` | `sample_rate`、`sample_by` |
| `05_custom_sink.py` | 自定义 sink |
| `06_fastapi_integration.py` | Middleware 自动注入 `request_id` |
| `07_stdlib_compat.py` | 桥接 `logging.getLogger()` |
| `08_colors_and_formatting.py` | 三层颜色体系 + `ColorScheme` 自定义 |

直接运行任意示例：

```bash
uv run python examples/01_quickstart.py
```

---

## 文档

| 文档 | 说明 |
|---|---|
| [TUTORIAL_CN.md](docs/TUTORIAL_CN.md) | 中文功能指南（含完整示例） |
| [TUTORIAL.md](docs/TUTORIAL.md) | English feature guide |
| [CLAUDE_CN.md](docs/CLAUDE_CN.md) | 架构参考（贡献者阅读） |
| [PROGRESS_CN.md](docs/PROGRESS_CN.md) | 设计决策记录 |

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

## 开源协议

MIT
