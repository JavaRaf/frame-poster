from cron_descriptor import get_description, FormatException
from pathlib import Path

from ruamel.yaml import YAML

from src.logger import get_logger

logger = get_logger(__name__)


def get_workflow_execution_interval(workflow_file: str | Path = ".github/workflows/01.yml") -> str | None:
    """
    Gets the workflow execution interval from a GitHub Actions workflow YAML file.
    
    Args:
        workflow_file: Path to the workflow YAML file. Defaults to ".github/workflows/01.yml".
    
    Returns:
        Human-readable interval such as "3", or None if not found/invalid.
    
    Example:
        >>> get_workflow_execution_interval(".github/workflows/01.yml")
        '3'
    """
    try:
        path = Path(workflow_file)
        if not path.exists():
            logger.warning("Workflow file not found: %s", path)
            return None
        
        yaml_parser = YAML()
        with path.open("r", encoding="utf-8") as file:
            workflow = yaml_parser.load(file)
        
        # Navigate to cron expression in workflow YAML
        cron_expression = None
        if isinstance(workflow, dict):
            schedule = workflow.get("on", {}).get("schedule", [])
            if schedule and isinstance(schedule, list):
                cron_expression = schedule[0].get("cron")
        
        if not cron_expression:
            logger.warning("No cron expression found in workflow file: %s", path)
            return None
        
        descriptor = get_description(cron_expression).replace("Every ", "").replace("hours", "")
        return descriptor
        
    except (FormatException, Exception) as exc:
        logger.error("Error parsing workflow or cron expression: %s", exc, exc_info=True)
        return None


