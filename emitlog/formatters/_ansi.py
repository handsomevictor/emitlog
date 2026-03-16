"""Low-level ANSI escape code rendering.

No external dependencies — pure Python implementation.
"""

from __future__ import annotations

import os

__all__ = ["ansi_color", "strip_ansi", "should_colorize"]

# Foreground color codes
_FG: dict[str, int] = {
    "black": 30,
    "red": 31,
    "green": 32,
    "yellow": 33,
    "blue": 34,
    "magenta": 35,
    "cyan": 36,
    "white": 37,
    "bright_black": 90,
    "bright_red": 91,
    "bright_green": 92,
    "bright_yellow": 93,
    "bright_blue": 94,
    "bright_magenta": 95,
    "bright_cyan": 96,
    "bright_white": 97,
}

# Background color codes (prefix "on ")
_BG: dict[str, int] = {
    "black": 40,
    "red": 41,
    "green": 42,
    "yellow": 43,
    "blue": 44,
    "magenta": 45,
    "cyan": 46,
    "white": 47,
}

# Modifier codes
_MODIFIERS: dict[str, int] = {
    "bold": 1,
    "dim": 2,
    "italic": 3,
    "underline": 4,
}

_RESET = "\033[0m"


def _parse_color_spec(color: str) -> list[int]:
    """Parse a color specification string into a list of ANSI codes.

    Handles:
    - Basic colors: "red", "green", etc.
    - Bright colors: "bright_red", "bright_green", etc.
    - Modifiers: "bold", "dim", "italic", "underline"
    - Background: "on red", "on green", etc.
    - Combined: "bold red", "dim cyan", "bold white on red"

    Unknown tokens are silently ignored.
    """
    codes: list[int] = []
    tokens = color.strip().split()
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token == "on" and i + 1 < len(tokens):
            # Background color
            bg_name = tokens[i + 1]
            if bg_name in _BG:
                codes.append(_BG[bg_name])
            i += 2
        elif token in _MODIFIERS:
            codes.append(_MODIFIERS[token])
            i += 1
        elif token in _FG:
            codes.append(_FG[token])
            i += 1
        else:
            # Unknown token — silently ignore
            i += 1
    return codes


def ansi_color(text: str, color: str | None) -> str:
    """Wrap ``text`` in ANSI escape codes for the given color.

    If ``color`` is None or empty, return ``text`` unchanged.
    """
    if not color:
        return text
    codes = _parse_color_spec(color)
    if not codes:
        return text
    code_str = ";".join(str(c) for c in codes)
    return f"\033[{code_str}m{text}{_RESET}"


def strip_ansi(text: str) -> str:
    """Remove all ANSI escape sequences from a string."""
    import re

    return re.sub(r"\033\[[0-9;]*m", "", text)


def should_colorize(colorize: bool, force_ansi: bool = False) -> bool:
    """Determine whether to emit ANSI color codes.

    Priority (highest to lowest):
    1. NO_COLOR=1 env var (https://no-color.org)
    2. EMITLOG_NO_COLOR=1 env var
    3. ``colorize`` parameter
    """
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("EMITLOG_NO_COLOR"):
        return False
    return colorize or force_ansi
