# PROGRESS_CN.md — emitlog 开发进度

## 状态总览

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
| `docs/` | ✅ | n/a | ✅ |

## 决策记录

### [_record.py] 使用 frozen dataclass

- **决策：** `LogRecord` 使用 `frozen=True`
- **原因：** 不可变性防止创建后被意外修改；符合规格要求
- **备选方案：** 普通 dataclass（可变，附加元数据更方便）

---

### [_span.py] 抛出 TypeError 而非返回 NotImplemented

- **决策：** 在 `__add__`/`__radd__` 中主动抛出 `TypeError`，而不是 `return NotImplemented`
- **原因：** mypy strict 模式要求返回类型为 `SpanList`，而 `NotImplemented` 是 `NotImplementedType`，不兼容
- **备选方案：** `return NotImplemented`（运行时正确，但 mypy 无法验证）

---

### [_serializer.py] 单函数 + 运行时分支

- **决策：** 单个 `serialize()` 函数内用 `if HAS_ORJSON` 分支
- **原因：** 避免条件函数定义让 mypy 报重复定义错误；代码更整洁
- **备选方案：** `if`/`else` 中各定义一个函数（需要 `# type: ignore[misc]`）

---

### [_context.py] 同一类同时支持 sync 和 async 上下文管理器

- **决策：** `_ContextManager` 同时实现 `__enter__`/`__exit__` 和 `__aenter__`/`__aexit__`
- **原因：** 让用户可以对同一对象使用 `with` 或 `async with`，无需区分
- **备选方案：** 两个独立类（代码更多，用户体验更差）

---

### [_event.py] 用 setattr() 设置类属性

- **决策：** 用 `setattr(dc, "__emitlog_level__", ...)` 而非 `dc.__emitlog_level__ = ...`
- **原因：** mypy strict 对 `type` 上的动态属性赋值报 `[attr-defined]` 错误
- **备选方案：** Protocol 类（更复杂），dataclasses Protocol（过度设计）

---

### [_logger.py] 通过 object.__setattr__ 附加 _field_meta

- **决策：** 创建 frozen `LogRecord` 后，用 `object.__setattr__(record, "_field_meta", field_meta)` 附加元数据
- **原因：** `LogRecord` 是 frozen（规格要求），但 `PrettyFormatter` 需要逐字段颜色元数据。将其放入 `LogRecord.fields` 会污染公开 API 和 JSON 序列化结果。
- **备选方案：** 直接在 `LogRecord` 加 `field_meta` 字段（改变公开 API）；通过 formatter 预调用传递（破坏职责分离）

---

### [sinks/_base.py] 类级变量声明 formatter

- **决策：** 在 `BaseSink` 声明 `formatter: BaseFormatter | None = None` 类级属性
- **原因：** mypy strict 需要 `self.formatter` 有明确声明，子类在 `__init__` 中赋值时才能通过类型检查
- **备选方案：** Protocol 方式；TypedDict；在 `_serialize()` 调用中传入 formatter

---

### [compat] 测试使用异步函数配合 sleep

- **决策：** compat 测试用 `@pytest.mark.asyncio` + `await asyncio.sleep(0.05)` 让 task 有机会执行
- **原因：** `_EmitlogHandler.emit()` 是同步的，但在异步测试循环中通过 `loop.create_task()` 调度；需要让出控制权
- **备选方案：** 手动操作事件循环（不稳定）

---

### [conftest.py] autouse fixture 重置全局配置

- **决策：** 添加 `autouse=True` fixture，每个测试后重置 emitlog 配置
- **原因：** `capture_stdlib=True` 把 root logger 设为 DEBUG，导致 asyncio 内部 debug 消息被捕获，引发后续测试的递归错误
- **备选方案：** 每个测试单独 teardown（容易遗漏）；模块级 fixture（仍有泄漏风险）

---

## ✅ ALL DONE
