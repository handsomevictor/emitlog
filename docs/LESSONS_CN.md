# LESSONS_CN.md — 踩坑记录与解决方案

## _span.py

### 问题
`__add__`/`__radd__` 方法中 `return NotImplemented` 导致 mypy strict 报错。

### 原因
mypy 看到返回类型为 `SpanList`，但 `NotImplemented` 是 `NotImplementedType`，类型不匹配。

### 解决方案
显式抛出 `TypeError`，而不是 return NotImplemented。对于本库的使用场景，效果完全等价——我们不需要 Python 的二元运算符反射回退机制。

### 预防措施
在 mypy strict 项目中编写魔术方法时，除非明确需要反射回退行为，否则优先用显式 raise 代替 `return NotImplemented`。

---

## _serializer.py

### 问题
在 `if HAS_ORJSON: ... else: ...` 块中条件定义 `serialize()` 函数，导致 else 分支需要 `type: ignore[misc]`。

### 原因
mypy 将第二次定义视为重复定义并报错。

### 解决方案
用单个函数 + 运行时 `if` 分支。代码更整洁，类型完全安全。

### 预防措施
对可选依赖的不同后端，避免条件函数定义，改用运行时分支。

---

## _config.py / _compat.py

### 问题
`capture_stdlib=True` 将 root logger 设为 `DEBUG`，导致 asyncio 内部消息被捕获，在测试中形成反馈循环，最终触发 `RecursionError`。

### 原因
`asyncio` 在 DEBUG 级别使用 Python 标准库 `logging`。当 emitlog 捕获 stdlib 日志时，这些 asyncio debug 消息也会被捕获，可能再触发更多 asyncio 操作，如此往复。

### 解决方案
1. 每个测试后通过 autouse fixture 将 emitlog 配置重置为 `capture_stdlib=False`。
2. 在 `_EmitlogHandler.emit()` 中过滤掉 `record.name.startswith('emitlog')` 的日志，防止 emitlog 自身日志被二次捕获。

### 预防措施
涉及全局状态时，测试隔离至关重要。务必提供 autouse teardown fixture 在每个测试后重置全局配置。

---

## _logger.py

### 问题
`LogRecord` 是 frozen dataclass，但 `PrettyFormatter` 需要不属于公开 schema 的逐字段元数据（`field_meta`）。

### 原因
`@dataclass(frozen=True)` 禁止属性赋值。如果把 `field_meta` 加入 `LogRecord`，它会变成公开 API 的一部分，并出现在 JSON 序列化结果中。

### 解决方案
创建 `LogRecord` 后，用 `object.__setattr__(record, "_field_meta", field_meta)` 绕过 frozen 检查。formatter 通过 `getattr(record, "_field_meta")` 读取。

### 预防措施
当需要通过 frozen dataclass 传递旁路数据时，先判断这些数据是否属于公开 API。若不属于，`object.__setattr__` 是合理的逃生舱，但必须有清晰的文档说明。

---

## sinks/_base.py

### 问题
mypy strict 要求 `self.formatter` 有明确声明，但子类在 `__init__` 中才设置它。

### 原因
`BaseSink._serialize()` 使用 `self.formatter`，但 mypy 在 `BaseSink` 中找不到该属性的声明。

### 解决方案
在 `BaseSink` 中声明 `formatter: BaseFormatter | None = None` 类级属性，子类在 `__init__` 中覆盖。

### 预防措施
使用 mypy strict 时，始终在类级别（或 `__init__`）声明实例属性。类级声明同时充当类型提示。

---

## examples/06_fastapi_integration.py

### 问题
`httpx.AsyncClient(app=app, base_url="http://test")` 在较新版本 httpx 中抛出 `TypeError`。

### 原因
`app` 参数在 httpx >= 0.20 中从 `AsyncClient.__init__` 移除，必须显式使用 `ASGITransport`。

### 解决方案
```python
transport = httpx.ASGITransport(app=app)
async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
    ...
```

### 预防措施
用 httpx 做 FastAPI 进程内测试时，始终使用 `ASGITransport` 模式——这是稳定 API。
