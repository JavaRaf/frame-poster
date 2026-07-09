"""
Logger module for application logging
"""

import logging
from pathlib import Path
import re

from src.settings import FB_LOG_PATH
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

FB_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
FB_LOG_PATH.touch(exist_ok=True)



# Constants
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

LOG_FILE = LOGS_DIR / "app.log"
LOG_FILE.touch(exist_ok=True)
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(module)s:%(funcName)s:%(lineno)d] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Patterns for sensitive data sanitization
SENSITIVE_PATTERNS = [
    (r"(?i)(access_token(?:%3D|=))([^&\s]+)", "access_token=***"),
]

# Timezone used by formatter.formatTime() — set via set_log_timezone().
_tz: ZoneInfo = ZoneInfo("UTC")


def set_log_timezone(tz_name: str) -> None:
    """Update the timezone used for ``%(asctime)s`` in all log handlers.

    Call this once after loading the configuration file.
    """
    global _tz
    try:
        _tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, KeyError):
        _tz = ZoneInfo("UTC")


def sanitize_log_message(message: str) -> str:
    """
    Sanitizes sensitive information from log messages.

    Args:
        message: The original log message.

    Returns:
        The sanitized message with sensitive data masked.
    """
    sanitized = message
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    return sanitized


class SanitizingFormatter(logging.Formatter):
    """Custom formatter that sanitizes sensitive information from log messages
    and uses the configured timezone for timestamps."""

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        dt = datetime.fromtimestamp(record.created, tz=_tz)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat()

    def format(self, record: logging.LogRecord) -> str:
        # Resolve the final formatted string first (msg % args), then sanitize it.
        # Clear args afterward so super().format() doesn't try to format again
        # and crash with "not all arguments converted during string formatting".
        original_message = record.getMessage()
        record.msg = sanitize_log_message(original_message)
        record.args = None
        return super().format(record)


def get_logger(name: str) -> logging.Logger:
    """
    Configures and returns a logger with sanitization for sensitive data.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance with sanitizing formatter.
    """
    # Create formatter with sanitization
    formatter = SanitizingFormatter(LOG_FORMAT, DATE_FORMAT)

    # File handler
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Configure logging
    logging.basicConfig(level=logging.ERROR, handlers=[file_handler, console_handler])

    return logging.getLogger(name)


# ── Facebook post log ─────────────────────────────────────────────────




def log_post_id(post_id: str, frame: int, episode: int, season: int, timezone: str) -> None:
    """Append a posted frame link to the Facebook log file.

    Args:
        post_id: The ID returned by the Facebook API.
        frame: The frame number that was posted.
        episode: The episode number.
        season: The season number.
        timezone: IANA timezone name (e.g. "America/Sao_Paulo").
    """

    try:
        tz = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, KeyError):
        tz = timezone.utc
    timestamp = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    entry = (
        f"[{timestamp}] S{season:02d}E{episode:02d}"
        f" | frame {frame}"
        f" | https://facebook.com/{post_id}\n"
    )
    try:
        with FB_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(entry)
    except OSError as e:
        logger = get_logger(__name__)
        logger.error(
            "Failed to append to fb log (%s): %s", FB_LOG_PATH, e, exc_info=True
        )
