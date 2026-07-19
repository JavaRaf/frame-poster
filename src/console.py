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


class DynamicTable:
    """A dynamically-built Rich table with key-value rows.

    Build rows incrementally via :meth:`add` and render with :meth:`print`.
    Supports method chaining: ``DynamicTable().add("A","1").add("B","2").print()``.
    """

    def __init__(
        self,
        border_style: str = "green",
        key_style: str = "bold cyan",
        value_style: str = "white",
    ) -> None:
        self._table = Table(
            box=box.ROUNDED,
            border_style=border_style,
            show_header=False,
            padding=(0, 1),
        )
        self._table.add_column("Key", style=key_style, no_wrap=True)
        self._table.add_column("Value", style=value_style)

    def add(self, key: str, value: str) -> "DynamicTable":
        """Add a row and return *self* for method chaining."""
        self._table.add_row(key, value)
        return self

    def print(self) -> None:
        """Render the table to the terminal."""
        console.print(self._table)
