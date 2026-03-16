"""JSON serialization for LogRecord.

Uses orjson for faster serialization when available (install with [fast] extra),
falls back to stdlib json.
"""

from __future__ import annotations

import json
from typing import Any

from emitlog._record import LogRecord

__all__ = ["serialize", "HAS_ORJSON"]

try:
    import orjson as _orjson_module

    HAS_ORJSON: bool = True
except ImportError:
    _orjson_module = None
    HAS_ORJSON = False


def _build_ordered_dict(record: LogRecord) -> dict[str, Any]:
    """Build the output dict in the required JSON field order.

    Output order: timestamp → level → logger_name → event_name →
                  **fields → **context
    """
    d: dict[str, Any] = {
        "timestamp": record.timestamp,
        "level": record.level,
        "logger_name": record.logger_name,
        "event_name": record.event_name,
    }
    d.update(record.fields)
    d.update(record.context)
    return d


def _default_json_encoder(obj: Any) -> str:
    """Fallback encoder for types not handled by stdlib json."""
    return str(obj)


def serialize(record: LogRecord) -> str:
    """Serialize a ``LogRecord`` to a JSON string."""
    d = _build_ordered_dict(record)
    if HAS_ORJSON and _orjson_module is not None:
        result: bytes = _orjson_module.dumps(d, default=_default_json_encoder)
        return result.decode("utf-8")
    return json.dumps(d, default=_default_json_encoder, ensure_ascii=False)
