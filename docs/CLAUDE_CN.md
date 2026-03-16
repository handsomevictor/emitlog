# CLAUDE_CN.md — emitlog 架构参考

## 一句话描述

emitlog 是一个为 Python 微服务设计的 asyncio 优先、类型安全、结构化日志库，零强制外部依赖。

## 核心架构

```
用户代码
    │
    ▼
get_logger(name) ──► Logger（无状态，emit 时读取全局配置）
    │
    ▼
@event 类实例 ──► Logger.emit(obj)
    │
    ├── 级别过滤（GlobalConfig.level_enabled）
    ├── 采样决策（should_emit: sample_rate + sample_by 哈希）
    ├── 上下文快照（contextvars._ctx.get()）
    ├── 构建 LogRecord（raw_fields 含 Span + fields 纯文本）
    │
    ▼
for sink in config.sinks:
    ├── sink.write(record) ──► Formatter.format(record) ──► 输出字符串
    │                              ├── PrettyFormatter: ANSI 彩色终端文本
    │                              └── JsonFormatter: JSON via _serializer.py
    └── （文件 sink：queue ──► 后台 Task ──► 文件）
```

## 关键文件职责

| 文件 | 职责 |
|------|------|
| `_record.py` | 不可变 `LogRecord` 数据类——流经整条管道的值对象 |
| `_span.py` | `Span`、`SpanList`、`colored()`、`span()`、`markup()`——行内颜色 API |
| `_serializer.py` | JSON 序列化；优先使用 `orjson`，否则回退到标准库 `json` |
| `_context.py` | 基于 `contextvars` 的上下文传播；`_ContextManager` 支持 sync/async |
| `_sampling.py` | `should_emit()`——确定性哈希采样或随机采样 |
| `_event.py` | `@event` 装饰器和 `field()`——将类转换为类型化日志事件 |
| `_config.py` | `_GlobalConfig` 单例，`configure()` 用 `threading.Lock` 保护写操作 |
| `_logger.py` | `Logger` 类——`emit()`、`emit_sync()`、`context()` |
| `_compat.py` | `_EmitlogHandler`——将标准库 `logging` 桥接到 emitlog sink |
| `formatters/_ansi.py` | 纯 Python ANSI 转义码生成（无外部依赖） |
| `formatters/_base.py` | `BaseFormatter` 抽象基类 |
| `formatters/_pretty.py` | `PrettyFormatter`、`ColorScheme`、`LevelColors` |
| `formatters/_json.py` | `JsonFormatter`——委托给 `_serializer.py` |
| `sinks/_base.py` | `BaseSink` 抽象基类，提供 `_serialize()` 辅助方法 |
| `sinks/_stderr.py` | `Stderr` sink——写入 `sys.stderr` |
| `sinks/_file.py` | `File`（同步）和 `AsyncFile`（异步队列 + 后台 Task） |

## 当前状态

| 模块 | 实现 | 测试 | 文档 |
|------|------|------|------|
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

## 已知问题与限制

- `emit_sync()` 不能在已运行的事件循环内调用（会抛出 RuntimeError，提示改用 `await log.emit()`）。
- `AsyncFile` 的后台 Task 必须通过 `await sink.close()` 才能 flush 剩余记录。
- `capture_stdlib=True` 在纯同步上下文中会对每条日志调用 `asyncio.run()`，创建新事件循环，不适合高吞吐量场景。
- `LogRecord` 是 frozen dataclass；`_field_meta` 通过 `object.__setattr__` 附加，以便在不污染公开 API 的前提下传递格式化元数据。

## 开发命令速查

```bash
# 运行所有测试
uv run pytest tests/ -v --tb=short

# 类型检查
uv run mypy emitlog --strict

# 运行单个示例
uv run python examples/01_quickstart.py

# 运行所有示例
uv run python examples/01_quickstart.py
uv run python examples/02_schema_events.py
uv run python examples/03_context.py
uv run python examples/04_sampling.py
uv run python examples/05_custom_sink.py
uv run python examples/06_fastapi_integration.py
uv run python examples/07_stdlib_compat.py
uv run python examples/08_colors_and_formatting.py
```
