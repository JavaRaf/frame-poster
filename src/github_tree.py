"""
GitHub Git Trees API client.

Lists available frame numbers directly from public or private repositories,
avoiding download failures of missing frames (404). Automatically falls back
to config.yml max_frames range on API failure.
"""

import os
import re
from functools import lru_cache

import httpx

from src.logger import get_logger

logger = get_logger(__name__)


def _parse_repo(github_repo: str) -> tuple[str, str, str, str]:
    """Parse github_repo path into (owner, repo, branch, path_prefix).

    Format: "username/repository/branch/optional/subfolders/"
    """
    parts = github_repo.strip("/").split("/")
    owner = parts[0]
    repo = parts[1]
    branch = parts[2]
    path_prefix = "/".join(parts[3:]) if len(parts) > 3 else ""
    return owner, repo, branch, path_prefix


@lru_cache(maxsize=16)
def _fetch_tree(owner: str, repo: str, branch: str) -> list[dict] | None:
    """Fetch the recursive tree from GitHub Git Trees API (cached per branch)."""
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}"
    params = {"recursive": "1"}
    headers = {"Accept": "application/vnd.github.v3+json"}

    # Actions automatically provides GITHUB_TOKEN or secrets can hold one
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        logger.info("Fetching Git Tree for %s/%s branch %s", owner, repo, branch)
        response = httpx.get(url, params=params, headers=headers, timeout=30)
        if response.status_code in (403, 429):
            logger.warning("GitHub API rate limit hit or token invalid while fetching tree")
            return None
        response.raise_for_status()
        return response.json().get("tree", [])
    except Exception as e:
        logger.warning("Failed to fetch tree from GitHub API: %s", e)
        return None


def list_frames(github_repo: str) -> list[int] | None:
    """List frame numbers available under the github_repo path prefix.

    Extracts numbers from files matching e.g. "01/0007.jpg".
    Returns a sorted list of ints, or None on failure (triggering fallback).
    """
    if not github_repo:
        return None

    try:
        owner, repo, branch, path_prefix = _parse_repo(github_repo)
    except IndexError:
        logger.error("Invalid github_repo config format: %s", github_repo)
        return None

    tree = _fetch_tree(owner, repo, branch)
    if tree is None:
        return None

    frame_numbers = []
    # Match frame numbers, allowing optional "frame_" prefix (e.g. "0001.jpg" or "frame_0001.jpg")
    pattern = re.compile(r"(?:^|/)(?:frame_)?(\d+)\.jpg$", re.IGNORECASE)

    for entry in tree:
        path = entry.get("path", "")
        # Filter by directory prefix (if specified)
        if path_prefix and not path.startswith(path_prefix):
            continue

        match = pattern.search(path)
        if match:
            frame_numbers.append(int(match.group(1)))

    if not frame_numbers:
        logger.warning("No .jpg frames found under path prefix '%s'", path_prefix)
        return None

    frame_numbers.sort()
    return frame_numbers
