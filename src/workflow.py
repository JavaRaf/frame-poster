from pathlib import Path

from src.logger import get_logger

logger = get_logger(__name__)


def get_workflow_execution_interval() -> str:
    """
    Gets the workflow execution interval from the workflow file.

    Returns:
        str: Interval in hours, formatted as a two-digit string
    """
    try:
        workflow_files = Path(".github/workflows").iterdir()
        for workflow_file in workflow_files:
            if workflow_file.suffix in [".yml", ".yaml"]:
                with workflow_file.open("r", encoding="utf-8") as file:
                    for line in file:
                        if line.strip().startswith("- cron:"):
                            cron_expression = line.split("cron:")[1].strip().strip('"')
                            parts = cron_expression.split()
                            if len(parts) == 5 and parts[1].startswith("*/"):
                                execution_interval = int(parts[1].replace("*/", ""))
                                return f"{execution_interval}"
    except Exception as e:
        logger.error(f"Error while getting workflow execution interval: {e}", exc_info=True)
        return "0"