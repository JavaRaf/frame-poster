import os
from pathlib import Path
from typing import Iterable

from src.settings import GITHUB_SUMMARY_PATH, LOCAL_SUMMARY_PATH


class SummaryWriter:
    def __init__(self, github_summary_path: str | None = None, local_path: Path | None = None):
        self.github_summary_path = github_summary_path or GITHUB_SUMMARY_PATH
        self.local_path = local_path or LOCAL_SUMMARY_PATH
        self.lines: list[str] = []

    def write(self, line: str = "") -> None:
        self.lines.append(line)

    def write_section(self, title: str) -> None:
        self.write(f"## {title}")

    def write_table(self, headers: Iterable[str], rows: Iterable[Iterable[str]]) -> None:
        self.write("| " + " | ".join(headers) + " |")
        self.write("|" + "|".join("---" for _ in headers) + "|")
        for row in rows:
            self.write("| " + " | ".join(row) + " |")

    def save(self) -> None:
        if self.local_path:
            self.local_path.parent.mkdir(parents=True, exist_ok=True)
            with self.local_path.open("w", encoding="utf-8") as local_file:
                local_file.write("\n".join(self.lines) + "\n")
        if self.github_summary_path:
            try:
                with open(self.github_summary_path, "a", encoding="utf-8") as gh_file:
                    gh_file.write("\n".join(self.lines) + "\n")
            except OSError:
                pass

    def clear(self) -> None:
        self.lines = []
