"""
Summary step for GitHub Actions

This script is used to generate a summary of the workflow execution.
It reads environment variables and generates a markdown table with the status of each variable.

"""

import os
from enum import Enum
from typing import Callable, Dict

# GitHub Actions GITHUB_STEP_SUMMARY environment variable or default to summary.md for local testing
SUMMARY_FILE = os.getenv("GITHUB_STEP_SUMMARY") or "summary.md"


class Status(Enum):
    """Status types for table rows."""

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


def write_summary(content: str) -> None:
    if SUMMARY_FILE:
        with open(SUMMARY_FILE, "a", encoding="utf-8") as f:
            f.write(content + "\n")


def format_success(text: str) -> str:
    """Return a success badge formatted for GitHub Actions summary output."""
    return f"$\\fbox{{\\color{{#2ea44f}}\\textsf{{✅  {text}}}}}$"  # latex mathjax


def format_error(text: str) -> str:
    """Return an error badge formatted for GitHub Actions summary output."""
    return f"$\\fbox{{\\color{{#d73a49}}\\textsf{{❌  {text}}}}}$"  # latex mathjax


def format_warning(text: str) -> str:
    """Return a warning badge formatted for GitHub Actions summary output."""
    return f"⚠️ {text}"


STATUS_FORMATTERS: Dict[Status, Callable[[str], str]] = {
    Status.SUCCESS: format_success,
    Status.ERROR: format_error,
    Status.WARNING: format_warning,
}


class SummaryTable:
    """Context manager for creating a summary table."""

    def __enter__(self):
        write_summary('<h1 align="center">Resume of execution</h1>')
        write_summary('<div align="center">')
        write_summary("\n| Variable | Status |")
        write_summary("|----------|---------|")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        write_summary("</div>")
        return False

    def add_row(self, key: str, value: str, status: Status) -> None:
        """Add a row to the table."""

        formatter = STATUS_FORMATTERS.get(status)

        if formatter:
            value = formatter(value)
        write_summary(f"| `{key}` | {value} |")


# # call this module directly for testing - e.g.: src/summary_step.py
# if __name__ == "__main__":
#     # Using context manager
#     with SummaryTable() as table:
#         table.add_row("VAR1", "value1", Status.SUCCESS)
#         table.add_row("VAR2", "value2", Status.ERROR)
#         table.add_row("VAR3", "value3", Status.WARNING)

#     print(f"Summary file: {SUMMARY_FILE}")
