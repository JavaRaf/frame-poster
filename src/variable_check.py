import os

import httpx

from src.logger import get_logger
from src.summary_step import Status, SummaryTable

logger = get_logger(__name__)


def check_fb_token(table: SummaryTable) -> None:
    """Check whether the Facebook token is present and valid."""
    fb_token = os.getenv("FB_TOKEN")
    if not fb_token:
        table.add_row("FB_TOKEN", "Token not found", Status.ERROR)
        return

    # Remove whitespace and newlines from token to prevent API errors
    fb_token = fb_token.strip()

    # Remove FB_TOKEN= prefix if present (common issue in CI/CD environments)
    if fb_token.startswith("FB_TOKEN="):
        fb_token = fb_token[8:]  # Remove "FB_TOKEN=" prefix

    # Debug information for troubleshooting
    logger.info(f"Token length: {len(fb_token)}")
    logger.info(f"Token starts with: {repr(fb_token[:20])}")
    logger.info(f"Token ends with: {repr(fb_token[-20:])}")
    logger.info(f"Token contains newlines: {'\\n' in fb_token}")
    logger.info(f"Token contains carriage returns: {'\\r' in fb_token}")

    try:
        response = httpx.get(
            "https://graph.facebook.com/v21.0/me",
            headers={"Authorization": f"Bearer {fb_token}"},
            timeout=15,
        )
        response.raise_for_status()
        fb_page_name = response.json().get("name")

        # Token is valid; display the page name for verification.
        table.add_row(
            "FB_TOKEN",
            f"Token is valid - {fb_page_name}",
            Status.SUCCESS,
        )

    except httpx.HTTPStatusError as e:
        # Note: intentionally not logging e.request.url here because it
        # embeds the raw access_token in the query string.
        logger.error(
            "FB_TOKEN check failed: HTTP %s - %s",
            e.response.status_code,
            e.response.text[:500],
        )
        table.add_row(
            "FB_TOKEN",
            f"HTTP error: {e.response.status_code}",
            Status.ERROR,
        )
    except httpx.RequestError as e:
        logger.error(
            "FB_TOKEN check failed: %s: %s", type(e).__name__, e
        )
        table.add_row(
            "FB_TOKEN",
            "Network error",
            Status.ERROR,
        )

