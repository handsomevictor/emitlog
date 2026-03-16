# TUTORIAL_CN.md — emitlog 功能指南

## 零配置启动

emitlog 开箱即用，无需任何配置。终端为 tty 或设置了 `EMITLOG_DEV=1` 时自动使用 `PrettyFormatter`，否则使用 `JsonFormatter`。`get_logger()` 在 import 阶段调用是安全的——不触发任何 IO。

```python
import emitlog
from emitlog import event

@event(level="info")
class AppStarted:
    version: str

log = emitlog.get_logger(__name__)

async def main():
    # 不调用 configure() 也能工作，使用默认配置
    await log.emit(AppStarted(version="1.0.0"))
```

### 常见错误

- **`TypeError: emit() requires an @event-decorated instance`** — 传入的是普通类实例，需要用 `@event` 装饰。

---

## configure()

`configure()` 替换所有 sink 和配置项，可多次调用，旧 sink 会被自动关闭。

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

### 常见错误

- **`capture_stdlib=True` 输出大量 debug 日志** — asyncio 在 DEBUG 级别写大量内部日志。将 `level` 设为 `"info"`，或在测试中避免启用 `capture_stdlib`。

---

## @event 装饰器

`@event` 同时将类变为 dataclass 和结构化日志事件，并将元数据（`__emitlog_level__`、`__emitlog_event_name__` 等）存储为类属性。

```python
from emitlog import event, field

@event(level="info")
class UserLogin:
    user_id: int
    ip: str
    user_agent: str = ""  # 默认值正常工作

# 使用方式：
obj = UserLogin(user_id=42, ip="1.2.3.4")
# 它是合法的 dataclass：
import dataclasses
print(dataclasses.asdict(obj))
```

### 常见错误

- **`ValueError: sample_by='nonexistent' is not a field`** — `sample_by` 指定的字段名不存在，检查拼写。
- **`ValueError: Field 'x' cannot have both 'color' and 'color_map'`** — `color` 和 `color_map` 只能选其一。

---

## field()

`dataclasses.field()` 的扩展版本，额外接受 `PrettyFormatter` 用于颜色渲染的注解参数。

```python
from emitlog import event, field

@event(level="info")
class HttpRequest:
    method: str = field(color="bold cyan")          # Layer 1: 字段静态颜色
    status_code: int = field(
        color_map=[                                  # Layer 2: 按值范围上色
            (range(200, 300), "bold green"),
            (range(400, 500), "bold yellow"),
            (range(500, 600), "bold red"),
        ]
    )
    duration_ms: float = field(
        color_map=[
            (range(0, 100),     "green"),
            (range(100, 500),   "yellow"),
            (range(500, 99999), "bold red"),
        ]
    )
```

### 常见错误

- **`ValueError: cannot have both 'color' and 'color_map'`** — 两者互斥：`color` 用于静态颜色，`color_map` 用于基于值的动态颜色。

---

## 行内片段上色

三层颜色体系中粒度最细的一层（Layer 3），通过 `colored()`、`span()` 和 `markup()` 实现。

```python
from emitlog import colored, span, markup

# colored() 和 span() 完全等价
msg1 = colored("SUCCESS", "bold green") + " deployed"
msg2 = span("ERROR", "bold red") + " something broke"

# markup() 解析 [color]text[/color] 语法
msg3 = markup("[bold green]SUCCESS[/bold green] to [bold red]prod[/bold red]")

# str(span_obj) 返回纯文本——可安全当作普通字符串使用
print(str(msg1))  # "SUCCESS deployed"
print(len(msg1))  # 17

# SpanList 算术运算
a = colored("i", "green")
b = colored("love", "red")
c = "you"  # 普通字符串被视为无色 Span
result = a + " " + b + " " + c  # 返回 SpanList
```

### 颜色语法

```
基础色：   black red green yellow blue magenta cyan white
亮色：     bright_black bright_red bright_green bright_yellow
           bright_blue bright_magenta bright_cyan bright_white
修饰符：   bold dim italic underline
组合：     "bold red"  "dim cyan"  "bold white on red"（on 后接背景色）
无色：     "" 或 None
```

### 常见错误

- **`TypeError: unsupported operand`** — 尝试将不支持的类型与 Span 相加。只有 `str`、`Span` 和 `SpanList` 可以组合。
- **markup() 中的未知颜色名** — 静默处理为无色，不抛出异常。

---

## 上下文传播

上下文字段自动添加到上下文块内所有日志记录中。基于 `contextvars` 实现，对 `asyncio.gather` 天然安全。

```python
async with log.context(request_id="abc", service="api"):
    await log.emit(UserLogin(user_id=1, ip="x"))
    # record.context == {"request_id": "abc", "service": "api"}

# 嵌套上下文：内层覆盖外层同名字段
async with log.context(service="api"):
    async with log.context(service="db"):
        # 此处 service == "db"
    # 恢复为 service == "api"

# asyncio.gather：每个协程上下文互相隔离
await asyncio.gather(task_a(), task_b())  # 不会串台
```

### 常见错误

- **上下文在异常后未恢复** — 上下文管理器保证在退出时恢复，无论是否有异常，这是有保障的。

---

## 采样

采样决策发生在序列化之前，高采样率场景下开销为零。

```python
# 1% 随机采样
@event(level="info", sample_rate=0.01)
class HealthCheckCalled:
    pass

# 按用户 ID 确定性采样（10%）
# 同一 user_id 总是做出相同的采样决策
@event(level="info", sample_rate=0.1, sample_by="user_id")
class ApiCalled:
    user_id: int
    endpoint: str
```

### 常见错误

- **`ValueError: sample_by='x' is not a field`** — 在装饰阶段抛出，检查字段名拼写。

---

## Sink（输出目标）

### Stderr

写入 `sys.stderr`，根据 tty 状态或 `EMITLOG_DEV` 自动选择 formatter。

```python
from emitlog.sinks import Stderr
from emitlog.formatters import PrettyFormatter

sink = Stderr(formatter=PrettyFormatter())
```

### File / AsyncFile

```python
from emitlog.sinks import File, AsyncFile

# 同步文件（每次写入后 flush）
sync_sink = File("app.log")

# 异步缓冲文件（后台 Task，基于队列）
async_sink = AsyncFile(
    "app.log",
    maxsize=10_000,
    overflow_policy="drop",  # 或 "block"
)
# 务必关闭 AsyncFile 以 flush 剩余记录
await async_sink.close()
```

### 自定义 Sink

```python
from emitlog.sinks import BaseSink
from emitlog._record import LogRecord

class DatadogSink(BaseSink):
    async def write(self, record: LogRecord) -> None:
        payload = self._serialize(record)  # 返回 JSON 字符串
        await send_to_datadog(payload)

    async def close(self) -> None:
        pass  # 可选清理
```

---

## Formatter（格式化器）

### PrettyFormatter

```python
from emitlog.formatters import PrettyFormatter, ColorScheme, LevelColors

fmt = PrettyFormatter(
    time_format="%H:%M:%S",
    columns=["time", "level", "event", "fields"],
    field_style="key=value",      # 或 "value_only"
    show_context_separator=True,
    colorize=True,
    force_ansi=False,             # 强制使用 ANSI（不用 rich）
    colors=ColorScheme(
        levels=LevelColors(info="bold blue"),
        event_name="bold yellow",
    ),
)
```

颜色关闭优先级：`NO_COLOR=1` > `EMITLOG_NO_COLOR=1` > `colorize=False`。

### JsonFormatter

```python
from emitlog.formatters import JsonFormatter
fmt = JsonFormatter()
# 输出单行 JSON，字段顺序：timestamp → level → logger_name → event_name → fields → context
```

### 自定义 Formatter

```python
from emitlog.formatters import BaseFormatter
from emitlog._record import LogRecord

class CompactFormatter(BaseFormatter):
    def format(self, record: LogRecord) -> str:
        return f"{record.level.upper()} {record.event_name}"
```

---

## 标准库兼容

```python
emitlog.configure(
    sinks=[...],
    capture_stdlib=True,  # 将标准库 logging 桥接到 emitlog
)

import logging
logging.getLogger("myapp").warning("旧代码照常工作")
# → 以 event_name="stdlib_log" 出现在 emitlog sink 中
```

### 常见错误

- **测试中出现无限循环/递归** — `capture_stdlib=True` + asyncio 在 DEBUG 级别会形成反馈循环。测试完成后务必重置为 `capture_stdlib=False`（使用 teardown fixture）。
