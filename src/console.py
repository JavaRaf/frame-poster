"""
Central Rich console module for styled terminal output.

Provides a shared Console instance and helper functions to keep
print-based output consistent, colorful, and easy to read.
"""

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich import box

# Shared console – use this everywhere instead of raw print().
console = Console()


def print_header(title: str) -> None:
    """Print a prominent header panel, e.g. for script start/end."""
    panel = Panel(
        Text(title, style="bold white", justify="center"),
        box=box.HEAVY,
        border_style="bright_blue",
        padding=(1, 2),
    )
    console.print(panel)


def print_separator() -> None:
    """Print a decorative horizontal rule."""
    console.print(Rule(style="dim white"))


def print_success(message: str) -> None:
    """Print a success status line with a green prefix."""
    console.print(f"  [bold green]✔[/] {message}")


def print_info(message: str) -> None:
    """Print an informational status line with a blue prefix."""
    console.print(f"  [bold bright_blue]├[/] {message}")


def print_leaf(message: str) -> None:
    """Print a leaf (last-item) status line with a purple prefix."""
    console.print(f"  [bold magenta]└[/] {message}")


def print_frame_posted(
    season: int,
    episode: int,
    frame: int,
    max_frames: int,
) -> None:
    """Print a styled table summarising a successfully posted frame."""
    table = Table(
        box=box.ROUNDED,
        border_style="green",
        show_header=False,
        padding=(0, 1),
    )
    table.add_column("Key", style="bold cyan", no_wrap=True)
    table.add_column("Value", style="white")

    table.add_row("Season", str(season))
    table.add_row("Episode", str(episode))
    table.add_row("Frame", f"{frame} / {max_frames}")

    console.print(table)
