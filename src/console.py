"""
Central Rich console module for styled terminal output.

Provides a shared Console instance and helper functions to keep
print-based output consistent, colorful, and easy to read.
"""

from rich.console import Console
from rich.rule import Rule



# Shared console – use this everywhere instead of raw print().
console = Console()


def print_separator() -> None:
    """Print a decorative horizontal rule."""
    console.print(Rule(style="dim white"))



"""
CLI argument parsing for frame-poster.
"""

import argparse


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run frame-poster with centralized config and token override."
    )
    
    parser.add_argument(
        "--fb-token",
        default=None,
        help="Facebook access token to use for this run. Overrides FB_TOKEN environment variable.",
    )
    return parser.parse_args(argv)

