"""@event decorator and field() helper for defining structured log events."""

from __future__ import annotations

import dataclasses
import re
from typing import Any

__all__ = ["event", "field"]

# Sentinel for emitlog-extended field metadata key
_EMITLOG_META_KEY = "__emitlog__"


def field(
    *,
    default: Any = dataclasses.MISSING,
    default_factory: Any = dataclasses.MISSING,
    repr: bool = True,
    hash: bool | None = None,
    init: bool = True,
    compare: bool = True,
    metadata: Any = None,
    kw_only: Any = dataclasses.MISSING,
    # emitlog extensions
    color: str | None = None,
    color_map: list[tuple[range | type, str]] | None = None,
) -> Any:
    """Extended dataclasses.field() with emitlog coloring metadata.

    Parameters
    ----------
    color:
        Static color for this field's value in PrettyFormatter.
    color_map:
        List of ``(range_or_type, color)`` tuples; matched in order.
        Mutually exclusive with ``color``.

    Raises
    ------
    ValueError
        If both ``color`` and ``color_map`` are specified (raised at
        ``@event`` decoration time, not here, so the error points to the
        class definition).
    """
    # Build emitlog-specific metadata dict
    emitlog_meta: dict[str, Any] = {}
    if color is not None:
        emitlog_meta["color"] = color
    if color_map is not None:
        emitlog_meta["color_map"] = color_map

    # Merge with any user-supplied metadata
    if metadata is None:
        merged_metadata: dict[str, Any] = {}
    else:
        merged_metadata = dict(metadata)
    if emitlog_meta:
        merged_metadata[_EMITLOG_META_KEY] = emitlog_meta

    # Build kwargs for dataclasses.field
    kwargs: dict[str, Any] = {
        "repr": repr,
        "hash": hash,
        "init": init,
        "compare": compare,
        "metadata": merged_metadata if merged_metadata else None,
    }
    if default is not dataclasses.MISSING:
        kwargs["default"] = default
    if default_factory is not dataclasses.MISSING:
        kwargs["default_factory"] = default_factory
    if kw_only is not dataclasses.MISSING:
        kwargs["kw_only"] = kw_only

    return dataclasses.field(**kwargs)


def _to_snake_case(name: str) -> str:
    """Convert CamelCase class name to snake_case event name."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def event(
    *,
    level: str = "info",
    sample_rate: float = 1.0,
    sample_by: str | None = None,
) -> Any:
    """Class decorator that turns a class into a structured log event.

    The decorated class is also a ``dataclass``.  Emitlog-specific metadata
    is stored as class attributes so it doesn't pollute ``__init__``.

    Parameters
    ----------
    level:
        Log level for this event (e.g. ``"info"``, ``"warning"``).
    sample_rate:
        Fraction of events to emit.  1.0 means all, 0.0 means none.
    sample_by:
        Field name to use for deterministic sampling.  The field must exist
        on the class; a ``ValueError`` is raised at decoration time if not.

    Raises
    ------
    ValueError
        If ``sample_by`` refers to a non-existent field, or if a ``field()``
        has both ``color`` and ``color_map`` set.
    """

    def decorator(cls: type) -> type:
        # Apply @dataclass first so we can inspect fields
        dc: type = dataclasses.dataclass(cls)

        field_names = {f.name for f in dataclasses.fields(dc)}

        # Validate sample_by
        if sample_by is not None and sample_by not in field_names:
            raise ValueError(
                f"@event sample_by={sample_by!r} is not a field of "
                f"{cls.__name__!r}. Available fields: {sorted(field_names)}"
            )

        # Build per-field metadata and validate color/color_map conflicts
        field_meta: dict[str, dict[str, Any]] = {}
        for f in dataclasses.fields(dc):
            meta = f.metadata.get(_EMITLOG_META_KEY, {})
            if meta:
                if "color" in meta and "color_map" in meta:
                    raise ValueError(
                        f"Field {f.name!r} in {cls.__name__!r} cannot have "
                        "both 'color' and 'color_map' set."
                    )
                # Validate color_map entries
                if "color_map" in meta:
                    for entry in meta["color_map"]:
                        if not isinstance(entry[0], (range, type)):
                            raise ValueError(
                                f"Field {f.name!r} color_map entry first element "
                                f"must be range or type, got {type(entry[0])!r}."
                            )
                field_meta[f.name] = meta

        # Attach emitlog metadata as class attributes
        # We use setattr to avoid mypy complaints about dynamic attributes on type
        setattr(dc, "__emitlog_level__", level.lower())
        setattr(dc, "__emitlog_sample_rate__", sample_rate)
        setattr(dc, "__emitlog_sample_by__", sample_by)
        setattr(dc, "__emitlog_field_meta__", field_meta)
        setattr(dc, "__emitlog_event_name__", _to_snake_case(cls.__name__))

        return dc

    return decorator
