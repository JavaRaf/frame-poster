"""
Logger module for application logging.
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

LOGS_DIR = Path() / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOG_FILE = LOGS_DIR / "app.log"
FACEBOOK_LOG = LOGS_DIR / "facebook.log"

LOG_FILE.touch(exist_ok=True)
FACEBOOK_LOG.touch(exist_ok=True)

LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(module)s:%(funcName)s:%(lineno)d] %(message)s"

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# ─────────────────────────────────────────────────────────────────────────────
# Timezone configuration
# ─────────────────────────────────────────────────────────────────────────────

# Default timezone: UTC-3
_log_timezone = timezone(timedelta(hours=-3))


def set_timezone_offset(offset_hours: int = 0) -> None:
    """
    Sets the global UTC offset used by the logging system.

    This function should be called once when the application starts,
    before creating the application loggers.

    Args:
        offset_hours:
            Offset from UTC in hours.

            Examples:
                -3 -> UTC-3
                 0 -> UTC
                 3 -> UTC+3
    """
    global _log_timezone

    _log_timezone = timezone(timedelta(hours=offset_hours))


# ─────────────────────────────────────────────────────────────────────────────
# Sensitive data sanitization
# ─────────────────────────────────────────────────────────────────────────────

SENSITIVE_PATTERNS = [
    (
        r"(?i)(access_token(?:%3D|=))([^&\s]+)",
        "access_token=***",
    ),
    (
        r"(?i)(malformed\s+access\s+token)\s+[^\s\"]+",
        r"\1 ***",
    ),
]


def sanitize_log_message(message: str) -> str:
    """
    Sanitizes sensitive information from log messages.

    Args:
        message:
            The original log message.

    Returns:
        The sanitized message with sensitive data masked.
    """
    sanitized = message

    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = re.sub(
            pattern,
            replacement,
            sanitized,
            flags=re.IGNORECASE,
        )

    return sanitized


# ─────────────────────────────────────────────────────────────────────────────
# Formatter
# ─────────────────────────────────────────────────────────────────────────────


class SanitizingFormatter(logging.Formatter):
    """
    Custom formatter that:

    - Sanitizes sensitive information from log messages.
    - Formats timestamps using the globally configured UTC offset.
    """

    def formatTime(
        self,
        record: logging.LogRecord,
        datefmt: str | None = None,
    ) -> str:
        """
        Formats the log record timestamp using the configured UTC offset.
        """
        dt = datetime.fromtimestamp(
            record.created,
            tz=_log_timezone,
        )

        if datefmt:
            return dt.strftime(datefmt)

        return dt.isoformat()

    def format(
        self,
        record: logging.LogRecord,
    ) -> str:
        """
        Sanitizes the final formatted log message.
        """
        # Resolve the final message first.
        original_message = record.getMessage()

        # Sanitize the resolved message.
        record.msg = sanitize_log_message(original_message)

        # Prevent logging.Formatter from trying to format
        # the arguments a second time.
        record.args = None

        return super().format(record)


# ─────────────────────────────────────────────────────────────────────────────
# Logger configuration
# ─────────────────────────────────────────────────────────────────────────────


def get_logger(
    name: str,
) -> logging.Logger:
    """
    Configures and returns a logger with sanitization.

    The logger uses the globally configured timezone offset.

    Args:
        name:
            Logger name, usually __name__.

    Returns:
        Configured logger instance.
    """

    formatter = SanitizingFormatter(
        LOG_FORMAT,
        DATE_FORMAT,
    )

    # File handler
    file_handler = logging.FileHandler(
        LOG_FILE,
        encoding="utf-8",
    )

    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()

    console_handler.setFormatter(formatter)

    # Configure logging
    logging.basicConfig(
        level=logging.ERROR,
        handlers=[
            file_handler,
            console_handler,
        ],
    )

    return logging.getLogger(name)


# ─────────────────────────────────────────────────────────────────────────────
# Default module logger
# ─────────────────────────────────────────────────────────────────────────────

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Facebook post log
# ─────────────────────────────────────────────────────────────────────────────


def log_post_id(
    post_id: str,
    frame: int,
    episode: int,
    season: int,
) -> None:
    """
    Appends a posted frame link to the Facebook log file.

    The timestamp uses the globally configured UTC offset.

    Args:
        post_id:
            The ID returned by the Facebook API.

        frame:
            The frame number that was posted.

        episode:
            The episode number.

        season:
            The season number.
    """

    if not post_id:
        logger.error(
            "Cannot log post ID: post_id is None for frame %s of episode %02d",
            frame,
            episode,
        )
        return

    timestamp = datetime.now(_log_timezone).strftime("%Y-%m-%d %H:%M:%S")

    entry = (
        f"[{timestamp}] "
        f"S{season:02d}E{episode:02d}"
        f" | frame {frame}"
        f" | https://facebook.com/{post_id}\n"
    )

    try:
        with FACEBOOK_LOG.open("a", encoding="utf-8") as f:
            f.write(entry)

    except OSError as e:
        logger.error(
            "Failed to append to fb log (%s): %s",
            FACEBOOK_LOG, e
        )
