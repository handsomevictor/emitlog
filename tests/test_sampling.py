"""Tests for _sampling.py."""

from __future__ import annotations

import pytest

from emitlog._sampling import should_emit


class TestSampling:
    def test_rate_1_always_emits(self) -> None:
        """sample_rate=1.0 records all — 1000 iterations, all pass."""
        for i in range(1000):
            assert should_emit(1.0, None, {"i": i}) is True

    def test_rate_0_drops_all(self) -> None:
        """sample_rate=0.0 drops all — 1000 iterations, all dropped."""
        for i in range(1000):
            assert should_emit(0.0, None, {"i": i}) is False

    def test_sample_by_same_value_idempotent(self) -> None:
        """sample_by same value always same result — 100 iterations."""
        for _ in range(100):
            result = should_emit(0.5, "user_id", {"user_id": 42})
            # Should always be same result for same value
            assert result == should_emit(0.5, "user_id", {"user_id": 42})

    def test_sample_by_different_values_distributed(self) -> None:
        """sample_by different values distributed reasonably — ±5% tolerance."""
        passed = sum(
            1 for i in range(1000)
            if should_emit(0.5, "user_id", {"user_id": i})
        )
        # Expect ~500, allow ±5% (±50)
        assert 450 <= passed <= 550, f"Expected ~500 passed, got {passed}"

    def test_sample_by_100_percent_all_pass(self) -> None:
        """With sample_by and 100%, all should pass."""
        for i in range(100):
            assert should_emit(1.0, "user_id", {"user_id": i}) is True

    def test_sample_by_0_percent_all_drop(self) -> None:
        """With sample_by and 0%, all should drop."""
        for i in range(100):
            assert should_emit(0.0, "user_id", {"user_id": i}) is False

    def test_sample_by_consistency_across_calls(self) -> None:
        """Same field value always gives same sampling decision."""
        results = {
            i: should_emit(0.3, "request_id", {"request_id": i})
            for i in range(100)
        }
        # Re-check same values — must be identical
        for i in range(100):
            assert should_emit(0.3, "request_id", {"request_id": i}) == results[i]

    def test_no_sample_by_is_random(self) -> None:
        """Without sample_by, use random sampling — distribution roughly correct."""
        rate = 0.5
        passed = sum(1 for _ in range(2000) if should_emit(rate, None, {}))
        # Very wide tolerance for random
        assert 700 <= passed <= 1300, f"Expected ~1000 passed, got {passed}"
