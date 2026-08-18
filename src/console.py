"""
Central Rich console module for styled terminal output.

Provides a shared Console instance and helper functions to keep
print-based output consistent, colorful, and easy to read.
"""

import argparse

import pyfiglet
from rich.console import Console
from rich.markup import escape

# Shared console – use this everywhere instead of raw print().
console = Console()

SEPARATOR = "______________________________________________________________________________________"


def print_header(season, episode, fph: int, total_episodes: int) -> None:
    """Print a styled ASCII art header before posting begins."""
    title = pyfiglet.figlet_format("Frame Poster", font="slant")
    console.print(f"[bold cyan]{title}[/bold cyan]")
    console.print(SEPARATOR)



def print_post_status(
    season: int | str,
    episode: int | str,
    total_episodes: int,
    frame: int,
    fph: int,
    max_frames: int,
    has_subtitles: bool,
    crop_ok: bool,
    repost_enabled: bool,
    album_name: str | None = None,
) -> None:
    """Print the per-frame posting status block to the console.

    Output format:
        ______________________________________________
        season      : 1
        episode     : 1/12
        frame       : 1/15
        subtitles   : [ok]
        random_crop : [ok]
        repost      : [ok] - album_name
        ______________________________________________
    """
    sub_status = escape("[ok]") if has_subtitles else escape("[--]")
    crop_status = escape("[ok]") if crop_ok else escape("[--]")
    if repost_enabled and album_name:
        repost_status = f"{escape('[ok]')} - {escape(album_name)}"
    else:
        repost_status = escape("[--]")

    lines = [
        f"season        : {season}",
        f"episode       : {episode}/{total_episodes}",
        f"frame         : {frame}/{fph} of {max_frames}" ,
        f"subtitles     : {sub_status}",
        f"random_crop   : {crop_status}",
        f"repost in     : {repost_status}",
        SEPARATOR,
    ]

    console.print("\n".join(lines))


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
