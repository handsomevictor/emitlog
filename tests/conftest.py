"""Shared pytest configuration and fixtures."""

from __future__ import annotations

import logging
from collections.abc import Generator

import pytest

import emitlog
from emitlog.sinks import Stderr


@pytest.fixture(autouse=True)
def reset_emitlog_config() -> Generator[None, None, None]:
    """Reset emitlog global config after each test to prevent state leakage."""
    yield
    # Disable stdlib capture to prevent asyncio debug logs from looping
    emitlog.configure(sinks=[Stderr()], level="info", capture_stdlib=False)
    # Also reset root logger level to WARNING to avoid debug log spam
    logging.root.setLevel(logging.WARNING)
