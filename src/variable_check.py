import os

import httpx

from src.facebook import sanitize_for_logging
from src.logger import get_logger

logger = get_logger(__name__)


SUMMARY_FILE = os.getenv("GITHUB_STEP_SUMMARY")


def write_to_summary(content: str) -> None:
    """Append a line to the GitHub Actions summary file, if available."""
    if SUMMARY_FILE:
        with open(SUMMARY_FILE, "a") as summary_file:
            summary_file.write(content + "\n")


# Report header for the variable validation summary is emitted when the check runs.


def format_success(text: str) -> str:
    """Return a success badge formatted for GitHub Actions summary output."""
    return f"$\\fbox{{\\color{{#126329}}\\textsf{{✅  {text}}}}}$"  # LaTeX MathJax


def format_error(text: str) -> str:
    """Return an error badge formatted for GitHub Actions summary output."""
    return f"$\\fbox{{\\color{{#82061E}}\\textsf{{❌  {text}}}}}$"  # LaTeX MathJax


def format_warning(text: str) -> str:
    """Return a warning badge formatted for GitHub Actions summary output."""
    return f"$\\fbox{{\\color{{#FFA500}}\\textsf{{⚠️  {text}}}}}$"  # LaTeX MathJax


def create_table_row(key: str, status: str) -> None:
    """Append a single summary row for one environment variable."""
    write_to_summary(f"| `{key}` | {status} |")


def run_variable_check() -> None:
    """Run the variable validation report and write the summary."""
    write_to_summary('<h1 align="center">Variable Verification</h1>')
    write_to_summary('<p align="center">Status of environment variables and tokens</p>')
    write_to_summary('<div align="center">')
    write_to_summary("\n| Variável | Status |")
    write_to_summary("|----------|---------|")


if __name__ == "__main__":
    run_variable_check()


# Validate the Facebook token and report its status.
def check_fb_token() -> None:
    """Check whether the Facebook token is present and valid."""
    fb_token = os.getenv("FB_TOKEN")
    if not fb_token:
        create_table_row("FB_TOKEN", format_error("Token not found"))
        return

    # Remove whitespace and newlines from token to prevent API errors
    fb_token = fb_token.strip()

    # Remove FB_TOKEN= prefix if present (common issue in CI/CD environments)
    if fb_token.startswith("FB_TOKEN="):
        fb_token = fb_token[8:]  # Remove "FB_TOKEN=" prefix

    # Debug information for troubleshooting
    print(f"Token length: {len(fb_token)}")
    print(f"Token starts with: {repr(fb_token[:20])}")
    print(f"Token ends with: {repr(fb_token[-20:])}")
    print(f"Token contains newlines: {'\\n' in fb_token}")
    print(f"Token contains carriage returns: {'\\r' in fb_token}")

    try:
        response = httpx.get(
            "https://graph.facebook.com/v21.0/me",
            headers={"Authorization": f"Bearer {fb_token}"},
            timeout=15,
        )
        response.raise_for_status()
        fb_page_name = response.json().get("name")

        # Token is valid; display the page name for verification.
        create_table_row("FB_TOKEN", format_success(f"Token is valid - {fb_page_name}"))

    except httpx.HTTPStatusError as e:
        # Note: intentionally not logging e.request.url here because it
        # embeds the raw access_token in the query string.
        logger.error(
            "FB_TOKEN check failed: HTTP %s - %s",
            e.response.status_code,
            e.response.text[:500],
        )
        create_table_row(
            "FB_TOKEN", format_error(f"HTTP error: {e.response.status_code}")
        )
    except httpx.RequestError as e:
        logger.error(
            "FB_TOKEN check failed: %s: %s", type(e).__name__, sanitize_for_logging(e)
        )
        create_table_row("FB_TOKEN", format_error("Network error"))


check_fb_token()
write_to_summary("\n</div>")
