"""08_colors_and_formatting.py — Colors, spans, and formatting.

Demonstrates:
1. Field-level colors (Layer 1): field(color="cyan")
2. Value-pattern coloring (Layer 2): field(color_map=[...])
3. Inline span coloring via colored() (Layer 3)
4. markup() syntax for inline rich-like markup
5. Custom ColorScheme
6. colorize=False (plain text, no color)
7. Terminal color + file JSON simultaneously
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

import emitlog
from emitlog import colored, event, field, markup, span
from emitlog.formatters import ColorScheme, LevelColors, PrettyFormatter
from emitlog.sinks import AsyncFile, Stderr


# ---- Layer 1: Field-level static colors ------------------------------------

@event(level="info")
class OrderCreated:
    order_id: str = field(color="cyan")          # Always cyan
    amount: float = field(color="bold green")     # Always bold green
    status: str = field(color="yellow")           # Always yellow


# ---- Layer 2: Value-pattern coloring ---------------------------------------

@event(level="info")
class HttpRequest:
    method: str = field(color="bold cyan")
    path: str = field(color="white")
    status_code: int = field(
        color_map=[
            (range(200, 300), "bold green"),
            (range(300, 400), "cyan"),
            (range(400, 500), "bold yellow"),
            (range(500, 600), "bold red"),
        ]
    )
    duration_ms: float = field(
        color_map=[
            (range(0, 100), "green"),
            (range(100, 500), "yellow"),
            (range(500, 99999), "bold red"),
        ]
    )


# ---- Layer 3: Inline span coloring ----------------------------------------

@event(level="info")
class DeployMessage:
    message: str  # Will hold a Span/SpanList


log = emitlog.get_logger(__name__)


async def main() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
        log_path = Path(f.name)

    print("=" * 60)
    print("Layer 1: Field-level colors")
    print("=" * 60)

    emitlog.configure(
        sinks=[Stderr(formatter=PrettyFormatter(colorize=True, force_ansi=True))],
        level="debug",
    )
    await log.emit(OrderCreated(order_id="ord-123", amount=99.99, status="pending"))
    await log.emit(OrderCreated(order_id="ord-456", amount=1500.00, status="completed"))

    print("\n" + "=" * 60)
    print("Layer 2: Value-pattern (color_map) coloring")
    print("=" * 60)

    await log.emit(HttpRequest(method="GET", path="/api/health", status_code=200, duration_ms=12.0))
    await log.emit(HttpRequest(method="POST", path="/api/slow", status_code=201, duration_ms=350.0))
    await log.emit(HttpRequest(method="DELETE", path="/api/data", status_code=404, duration_ms=5.0))
    await log.emit(HttpRequest(method="GET", path="/api/broken", status_code=500, duration_ms=600.0))

    print("\n" + "=" * 60)
    print("Layer 3: Inline span coloring with colored()")
    print("=" * 60)

    # colored() / span() create Span objects
    msg1 = colored("i", "green") + " " + colored("love", "red") + " " + colored("you", "blue")
    # span() is an alias for colored()
    msg2 = span("ERROR", "bold white on red") + " " + span("something went wrong", "red")
    await log.emit(DeployMessage(message=msg1))  # type: ignore[arg-type]
    await log.emit(DeployMessage(message=msg2))  # type: ignore[arg-type]

    print("\n" + "=" * 60)
    print("markup() syntax")
    print("=" * 60)

    msg3 = markup("[bold green]SUCCESS[/bold green] deployed to [bold red]production[/bold red]")
    msg4 = markup("[cyan]INFO[/cyan] [white]server started on port [bold]8080[/bold][/white]")
    await log.emit(DeployMessage(message=msg3))  # type: ignore[arg-type]
    await log.emit(DeployMessage(message=msg4))  # type: ignore[arg-type]

    print("\n" + "=" * 60)
    print("Custom ColorScheme")
    print("=" * 60)

    custom_scheme = ColorScheme(
        levels=LevelColors(info="bold blue", warning="bold magenta"),
        timestamp="green",
        logger_name="bold white",
        event_name="bold yellow",
        field_key="dim white",
        field_value="bright_white",
        context_key="dim green",
        context_value="bright_green",
    )
    emitlog.configure(
        sinks=[Stderr(formatter=PrettyFormatter(
            colorize=True,
            force_ansi=True,
            colors=custom_scheme,
        ))],
        level="debug",
    )
    await log.emit(OrderCreated(order_id="ord-789", amount=42.0, status="active"))

    print("\n" + "=" * 60)
    print("colorize=False (plain text, no ANSI codes)")
    print("=" * 60)

    emitlog.configure(
        sinks=[Stderr(formatter=PrettyFormatter(colorize=False))],
        level="debug",
    )
    await log.emit(OrderCreated(order_id="ord-plain", amount=10.0, status="plain"))

    print("\n" + "=" * 60)
    print("Terminal (colored) + File (JSON) simultaneously")
    print("=" * 60)

    async_file = AsyncFile(log_path)
    emitlog.configure(
        sinks=[
            Stderr(formatter=PrettyFormatter(colorize=True, force_ansi=True)),
            async_file,
        ],
        level="debug",
    )

    await log.emit(HttpRequest(method="GET", path="/api/dual", status_code=200, duration_ms=55.0))
    await log.emit(OrderCreated(order_id="ord-dual", amount=75.0, status="shipped"))

    # Close the async file sink to flush
    await async_file.close()

    # Show the JSON file content
    print(f"\nJSON file content ({log_path}):")
    with open(log_path) as f:
        for line in f:
            data = json.loads(line.strip())
            print(f"  {data['event_name']}: {data}")


if __name__ == "__main__":
    asyncio.run(main())
