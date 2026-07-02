"""
This module provides functions to calculate the average run interval of a GitHub Actions workflow.
"""

from datetime import datetime
from pathlib import Path
from statistics import mean

import yaml
from croniter import croniter

# {'name': 'init banner', True: {'workflow_dispatch': None, 'schedule': [{'cron': '0 */3 * * *'}]}}


def get_cron_iterator(file_path: str = ".github/workflows/01.yml") -> croniter:
    """
    Returns a croniter object representing the cron schedule.

    Args:
        file_path: The path to the workflow file (relative to project root).

    Returns:
        A croniter object representing the cron schedule.
    """
    try:
        if not Path(file_path).is_absolute():
            file_path = Path(__file__).parent.parent / file_path
        
        with Path(file_path).open("r") as f:
            content: dict = yaml.safe_load(f)
            return croniter(content.get(True).get("schedule")[0].get("cron"))
    except Exception as e:
        print(e)


def calculate_average_run_interval(cron_iter: croniter, runs: int = 20) -> float:
    """
    Calculates the average run interval in seconds.

    Args:
        cron_iter: A croniter object representing the cron schedule.
        runs: The number of runs to calculate the average interval for.

    Returns:
        The average run interval in seconds.
    """
    intervals = []

    # Discard first run for improved accuracy
    prev_time = cron_iter.get_next(datetime)

    for _ in range(runs):
        next_time = cron_iter.get_next(datetime)
        interval = (next_time - prev_time).total_seconds()
        intervals.append(interval)
        prev_time = next_time

    return mean(intervals)


def get_workflow_interval() -> str | None:
    """
    Returns interval in hours.
    """
    cron_iter = get_cron_iterator()
    return f"{int(calculate_average_run_interval(cron_iter) / 3600)}"

