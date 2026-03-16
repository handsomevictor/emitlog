# TESTING_CN.md — 测试套件说明

## 本地运行测试

### 前置条件

安装开发依赖（包含 pytest、pytest-asyncio、mypy 等）：

```bash
uv sync --extra dev
```

### 运行所有测试

```bash
uv run pytest tests/ -v
```

### 常用参数

```bash
# 失败时输出简短 traceback（日常开发推荐）
uv run pytest tests/ -v --tb=short

# 只运行单个测试文件
uv run pytest tests/test_span.py -v

# 只运行单个测试用例
uv run pytest tests/test_context.py::TestContextAsync::test_context_isolation_in_gather -v

# 按关键词过滤
uv run pytest tests/ -v -k "color"

# 遇到第一个失败立即停止
uv run pytest tests/ -x

# 显示 print() 输出（调试时有用）
uv run pytest tests/ -v -s

# 同时跑类型检查（与测试一起运行）
uv run mypy emitlog --strict
```

### 预期结果

全部 119 个测试应零报错通过：

```
============================= 119 passed in 0.32s ==============================
```

---

## 测试文件详解

### `conftest.py` — 共享 Fixture

包含一个对**每个测试**都自动生效的 `autouse=True` fixture：

- **`reset_emitlog_config`** — 每个测试结束后将 emitlog 全局配置重置为默认值，并将标准库 root logger 恢复为 `WARNING` 级别。防止测试间状态泄漏（尤其是启用了 `capture_stdlib=True` 的情况——否则 asyncio debug 日志会在后续测试中形成反馈循环）。

---

### `test_span.py` — 行内颜色片段

测试 `_span.py` 中的 `Span`、`SpanList`、`colored()`、`span()`、`markup()`。

**`TestSpan`**

| 测试 | 验证内容 |
|---|---|
| `test_colored_returns_span` | `colored("x", "red")` 返回 `Span` 实例 |
| `test_str_gives_plain_text` | `str(span)` 返回原始文本，不含 ANSI 码 |
| `test_repr` | `repr(span)` 返回 `Span('x', 'red')` 格式 |
| `test_len` | `len(span)` 返回纯文本的字符长度 |
| `test_span_alias` | `span()` 是 `colored()` 的完全别名 |
| `test_span_plus_span_returns_spanlist` | `Span + Span` 返回 `SpanList` |
| `test_span_plus_str_returns_spanlist` | `Span + str` 返回 `SpanList`，字符串被视为无色 Span |
| `test_str_plus_span_radd` | `str + Span` 通过 `__radd__` 实现，返回 `SpanList` |
| `test_span_plus_spanlist` | `Span + SpanList` 将 Span 追加到列表 |
| `test_equality` | 文本和颜色相同的两个 `Span` 对象相等 |

**`TestSpanList`**

| 测试 | 验证内容 |
|---|---|
| `test_str_returns_plain_text` | `str(spanlist)` 将所有 span 的文本拼接为纯文本 |
| `test_len_returns_plain_text_length` | `len(spanlist)` 是所有 span 纯文本长度之和 |
| `test_spanlist_plus_span` | `SpanList + Span` 追加该 span |
| `test_spanlist_plus_str` | `SpanList + str` 追加一个无色 span |
| `test_spanlist_plus_spanlist` | `SpanList + SpanList` 合并两个列表 |
| `test_str_radd_spanlist` | `str + SpanList` 通过 `__radd__` 在头部插入无色 span |

**`TestMarkup`**

| 测试 | 验证内容 |
|---|---|
| `test_basic_color_tag` | `[red]text[/red]` 解析为颜色为 `"red"` 的 `Span` |
| `test_plain_text` | 无标签的纯文本返回含一个无色 span 的 `SpanList` |
| `test_multiple_tags` | 多个并列标签各自成为独立的 `Span` |
| `test_nested_tags` | 嵌套标签如 `[bold][red]x[/red][/bold]` 能正确解析 |
| `test_unknown_color_no_error` | 未知标签名不抛出异常，视为无色 |
| `test_unbalanced_tags_no_error` | 未闭合的开标签不抛出异常 |
| `test_unbalanced_close_no_error` | 孤立的闭标签不抛出异常 |
| `test_complex_markup` | 单个字符串中混合已知/未知标签 |
| `test_empty_string` | `markup("")` 返回空 `SpanList` |
| `test_mixed_colored_and_plain` | 含有标签和无标签部分的混合字符串 |

---

### `test_context.py` — 上下文传播

测试 `_context.py` 中的 `_ContextManager` 和 `get_current_context()`。

**`TestContextSync`**

| 测试 | 验证内容 |
|---|---|
| `test_single_layer_context_injected` | 传入 `with log.context(...)` 的字段出现在 `get_current_context()` 中 |
| `test_context_restored_after_exit` | `with` 块退出后所有字段消失 |
| `test_nested_inner_overrides_outer` | 内层上下文覆盖外层同名字段 |
| `test_nested_outer_restored_after_inner_exit` | 内层退出后外层的值被正确恢复 |
| `test_exception_restores_context` | 块内抛出异常后，退出时上下文仍被恢复 |
| `test_sync_context_manager_works` | 同步 `with` 形式正常工作 |

**`TestContextAsync`**

| 测试 | 验证内容 |
|---|---|
| `test_async_single_layer` | `async with log.context(...)` 注入字段 |
| `test_async_nested` | 嵌套 `async with` 块正确嵌套和恢复 |
| `test_async_exception_restores` | `async with` 块内异常后上下文仍被恢复 |
| `test_context_isolation_in_gather` | **关键边界场景**：`asyncio.gather` 中两个并发协程各自维护完全独立的上下文，互不干扰 |

---

### `test_event.py` — @event 装饰器与 field()

测试 `_event.py` 中的 `@event`、`field()` 及装饰阶段的校验逻辑。

| 测试 | 验证内容 |
|---|---|
| `test_decorated_class_is_dataclass` | `@event` 装饰后的类是合法 dataclass（通过 `dataclasses.is_dataclass()` 验证） |
| `test_instantiation_works` | 可用位置参数和关键字参数正常实例化 |
| `test_missing_required_field_raises_typeerror` | 缺少必填字段时实例化抛出 `TypeError`（标准 dataclass 行为） |
| `test_sample_by_nonexistent_field_raises_valueerror` | `sample_by="不存在的字段"` 在**装饰阶段**抛出 `ValueError`，而非运行时 |
| `test_field_color_and_color_map_raises_valueerror` | 同一字段同时指定 `color=` 和 `color_map=` 在装饰阶段抛出 `ValueError` |
| `test_color_map_range_matching` | 不同范围内的值映射到正确的颜色字符串 |
| `test_event_name_snake_case` | `UserLogin` → `"user_login"` |
| `test_event_name_complex_snake_case` | `HTTPRequestLog` → `"http_request_log"` |
| `test_metadata_attributes_set` | `__emitlog_level__`、`__emitlog_sample_rate__`、`__emitlog_event_name__` 被正确设置在类上 |
| `test_field_with_color_metadata` | `field(color="cyan")` 将颜色元数据存储在 `__emitlog_field_meta__` 中 |
| `test_field_with_color_map` | `field(color_map=[...])` 正确存储颜色映射元数据 |
| `test_sample_rate_default_is_1` | 默认 `sample_rate` 为 `1.0` |
| `test_health_check_with_sample_rate` | `sample_rate=0.01` 被正确存储 |
| `test_emit_non_event_raises_typeerror` | 将非 `@event` 实例传入 `emit()` 抛出 `TypeError` |

---

### `test_sampling.py` — 采样逻辑

测试 `_sampling.py` 中的 `should_emit()`。

| 测试 | 验证内容 |
|---|---|
| `test_rate_1_always_emits` | `sample_rate=1.0`：1000 次调用全部返回 `True` |
| `test_rate_0_drops_all` | `sample_rate=0.0`：1000 次调用全部返回 `False` |
| `test_sample_by_same_value_idempotent` | 相同 `sample_by` 值 100 次调用结果始终相同（幂等性） |
| `test_sample_by_different_values_distributed` | 1000 个不同值在 `sample_rate=0.5` 时，结果在 50% ± 5% 范围内 |
| `test_sample_by_100_percent_all_pass` | `sample_by` + `sample_rate=1.0`：全部通过 |
| `test_sample_by_0_percent_all_drop` | `sample_by` + `sample_rate=0.0`：全部丢弃 |
| `test_sample_by_consistency_across_calls` | 同一字段值跨多次调用决策一致，可确定性验证 |
| `test_no_sample_by_is_random` | 不设 `sample_by` 时采用随机采样，分布符合期望 |

---

### `test_serializer.py` — JSON 序列化

测试 `_serializer.py` 中的 `serialize()`。

| 测试 | 验证内容 |
|---|---|
| `test_returns_valid_json` | 输出可被 `json.loads()` 解析 |
| `test_field_order` | 键顺序为：`timestamp → level → logger_name → event_name → fields → context` |
| `test_fields_before_context` | 事件字段在上下文字段之前出现 |
| `test_basic_values` | 字符串、整数、浮点数正确序列化 |
| `test_empty_fields_and_context` | 空 `fields` 和 `context` 产生干净的 JSON |
| `test_non_serializable_uses_str` | 不可序列化的对象回退到 `str()` |
| `test_unicode_values` | Unicode 字符正确序列化 |

---

### `test_formatters.py` — PrettyFormatter 与 JsonFormatter

测试 `formatters/` 下所有格式化器。

**`TestPrettyFormatter`**

| 测试 | 验证内容 |
|---|---|
| `test_output_contains_all_fields` | 格式化后的字符串包含所有事件字段的键和值 |
| `test_output_contains_timestamp` | 时间戳出现在输出中 |
| `test_output_contains_level` | 日志级别出现在输出中 |
| `test_colorize_false_no_ansi` | `colorize=False` 时输出中零 ANSI 转义码（`\033[`） |
| `test_colorize_true_has_ansi` | `colorize=True` 时输出包含 ANSI 转义码 |
| `test_no_color_env_disables_colors` | `NO_COLOR=1` 环境变量移除所有 ANSI 码，无论 `colorize` 设置 |
| `test_emitlog_no_color_env_disables_colors` | `EMITLOG_NO_COLOR=1` 环境变量同样移除 ANSI 码 |
| `test_span_field_rendered_with_color` | `Span` 类型字段在输出中带有对应的 ANSI 颜色 |
| `test_span_field_plain_when_no_color` | `colorize=False` 时 `Span` 字段渲染为纯文本 |
| `test_spanlist_field_rendered` | `SpanList` 字段中每个 span 都带有各自的 ANSI 颜色 |
| `test_color_map_applies_correct_color` | 含 `color_map` 的字段根据值范围应用正确颜色 |
| `test_custom_color_scheme` | 自定义 `ColorScheme` 改变输出中使用的颜色 |
| `test_context_separator_shown` | `show_context_separator=True` 在字段和上下文之间显示 `│` |
| `test_context_separator_hidden` | `show_context_separator=False` 隐藏分隔符 |
| `test_value_only_field_style` | `field_style="value_only"` 省略 `key=` 前缀 |

**`TestJsonFormatter`**

| 测试 | 验证内容 |
|---|---|
| `test_returns_valid_json` | 输出可被 `json.loads()` 解析 |
| `test_span_field_as_plain_text` | `Span` 字段在 JSON 中表示为纯文本字符串（无 ANSI） |
| `test_spanlist_as_plain_text` | `SpanList` 字段在 JSON 中表示为拼接后的纯文本 |
| `test_no_ansi_in_output` | JSON 输出不含任何 ANSI 转义码 |
| `test_field_order` | JSON 键遵循规定顺序 |

---

### `test_sinks.py` — Sink 输出目标

测试 `sinks/` 下的 `Stderr`、`File`、`AsyncFile` 及自定义 sink。

**`TestStderr`**

| 测试 | 验证内容 |
|---|---|
| `test_writes_to_stderr` | 输出出现在 stderr（通过 `capsys` 捕获验证） |
| `test_close_is_noop` | `await sink.close()` 不抛出异常 |
| `test_pretty_formatter_used_in_dev_mode` | `EMITLOG_DEV=1` 环境变量使 `Stderr` 自动选择 `PrettyFormatter` |
| `test_custom_formatter` | 传入 `Stderr()` 的自定义 formatter 被实际使用 |

**`TestFile`**

| 测试 | 验证内容 |
|---|---|
| `test_writes_to_file` | 输出被写入文件且是合法 JSON |
| `test_appends_to_file` | 多次写入追加行，文件行数正确 |
| `test_custom_formatter` | 传入 `File()` 的自定义 formatter 被实际使用 |
| `test_default_json_formatter` | 不传 formatter 时 `File` 默认使用 `JsonFormatter` |

**`TestAsyncFile`**

| 测试 | 验证内容 |
|---|---|
| `test_writes_to_file` | `close()` 后输出被 flush 并写入文件 |
| `test_lazy_start` | 后台 Task 在 `__init__` 时**不**启动，仅在第一次 `write()` 时启动 |
| `test_multiple_records` | 多条记录在 `close()` 后全部出现在文件中 |
| `test_drop_overflow_policy` | `overflow_policy="drop"` 下队列满时额外记录被静默丢弃（不抛异常） |

**`TestCustomSink`**

| 测试 | 验证内容 |
|---|---|
| `test_custom_sink_can_serialize` | `BaseSink` 子类可调用 `self._serialize(record)` 并得到合法 JSON 字符串 |

---

### `test_logger.py` — Logger

测试 `_logger.py` 中的 `get_logger()`、`emit()`、`emit_sync()`、`context()`。

**`TestGetLogger`**

| 测试 | 验证内容 |
|---|---|
| `test_returns_logger` | `get_logger("name")` 返回 `Logger` 实例 |
| `test_same_name_same_instance` | 同名两次调用 `get_logger` 返回同一对象 |

**`TestEmit`**

| 测试 | 验证内容 |
|---|---|
| `test_emit_event_works` | emit 有效的 `@event` 实例后 sink 收到一条 `LogRecord` |
| `test_emit_non_event_raises_typeerror` | emit 普通类实例抛出 `TypeError` |
| `test_level_filtering` | 低于配置级别的记录被丢弃 |
| `test_sampling_zero_drops_all` | `sample_rate=0.0` 的事件不写入 sink |
| `test_context_injected` | `log.context()` 中设置的字段出现在 `record.context` 中 |
| `test_nested_context` | 嵌套上下文在 emit 的记录中正确合并和恢复 |
| `test_span_field_plain_in_fields` | `record.fields` 含纯文本；`record.raw_fields` 含原始 `Span` 对象 |
| `test_logger_name_in_record` | `record.logger_name` 与 `get_logger()` 传入的名称一致 |
| `test_timestamp_format` | `record.timestamp` 符合 ISO 8601 UTC 含毫秒格式 |
| `test_gather_context_isolation` | `asyncio.gather` 中两个协程各自产生带独立上下文的记录 |

**`TestEmitSync`**

| 测试 | 验证内容 |
|---|---|
| `test_emit_sync_works` | `log.emit_sync(...)` 在异步上下文之外正常工作 |
| `test_emit_sync_in_async_raises` | 在协程内部调用 `log.emit_sync(...)` 抛出 `RuntimeError`，并附有明确提示 |

**`TestContextManager`**

| 测试 | 验证内容 |
|---|---|
| `test_sync_context_works` | `with log.context(...)` 在同步代码中正确注入和恢复字段 |

---

### `test_compat.py` — 标准库兼容

测试 `_compat.py` 中的 `_EmitlogHandler`。

| 测试 | 验证内容 |
|---|---|
| `test_capture_stdlib_true_registers_handler` | `capture_stdlib=True` 将标准库 `logging` 调用路由到 emitlog sink |
| `test_capture_stdlib_false_no_handler` | `capture_stdlib=False` 不安装 handler |
| `test_stdlib_log_event_name` | 桥接的记录 `event_name` 始终为 `"stdlib_log"` |
| `test_emitlog_own_logs_not_captured` | emitlog 自身的内部日志不会被二次捕获（防止无限循环） |
| `test_reconfigure_removes_old_handler` | 再次调用 `configure()` 干净地移除旧的 stdlib handler |
| `test_warning_level_mapped_correctly` | 标准库 `WARNING` 级别映射为 emitlog 中的 `"warning"`（而非 `"warn"`） |
