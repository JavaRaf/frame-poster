import re
from pathlib import Path

from src.logger import get_logger

logger = get_logger(__name__)


def _parse_cron_interval(cron_expression: str) -> str:
    """Return a human-readable interval for the workflow cron expression."""
    parts = cron_expression.split()
    if len(parts) != 5:
        return "0"

    minute, hour, day_of_month, month, day_of_week = parts

    if minute == "0" and hour.startswith("*/"):
        interval = int(hour.replace("*/", ""))
        return f"{interval} hour" if interval == 1 else f"{interval} hours"

    if minute == "0" and hour == "0" and day_of_month.startswith("*/"):
        interval = int(day_of_month.replace("*/", ""))
        return f"{interval} day" if interval == 1 else f"{interval} days"

    if minute == "0" and hour == "0" and day_of_month == "*" and month == "*" and day_of_week == "*":
        return "1 day"

    return "0"


def get_workflow_execution_interval(workflow_file: str | Path = ".github/workflows/01.yml") -> str:
    """
    Gets the workflow execution interval from the workflow file.

    Returns:
        str: Human-readable interval such as "3 hours" or "1 day".
    """
    try:
        path = Path(workflow_file)
        if not path.exists():
            logger.warning("Workflow file not found: %s", path)
            return "0"

        with path.open("r", encoding="utf-8") as file:
            for line in file:
                match = re.search(r"cron:\s*['\"]?([^'\"]+)['\"]?", line)
                if not match:
                    continue

                return _parse_cron_interval(match.group(1).strip())
    except Exception as exc:
        logger.error("Error while getting workflow execution interval: %s", exc, exc_info=True)

    return "0"