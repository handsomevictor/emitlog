"""Sampling logic for emitlog events.

Sampling decision is made at emit() entry, before serialization.
"""

from __future__ import annotations

from typing import Any

__all__ = ["should_emit"]

_SAMPLE_PRECISION = 10_000


def _hash_value(value: Any) -> int:
    """Hash a value to a bucket in [0, _SAMPLE_PRECISION)."""
    return hash(str(value)) % _SAMPLE_PRECISION


def should_emit(
    sample_rate: float,
    sample_by: str | None,
    fields: dict[str, Any],
) -> bool:
    """Return True if the event should be emitted.

    Parameters
    ----------
    sample_rate:
        1.0 → always emit (no hashing), 0.0 → never emit.
    sample_by:
        If given, use the value of this field for deterministic hashing.
        If None, use a per-call hash (effectively random).
    fields:
        The event field values dict.
    """
    if sample_rate >= 1.0:
        return True
    if sample_rate <= 0.0:
        return False

    threshold = int(sample_rate * _SAMPLE_PRECISION)

    if sample_by is not None:
        bucket = _hash_value(fields[sample_by])
    else:
        # No sample_by: use hash of all field values combined (non-deterministic
        # between processes, deterministic within a single call for same data).
        import os

        bucket = int.from_bytes(os.urandom(2), "big") % _SAMPLE_PRECISION

    return bucket < threshold
