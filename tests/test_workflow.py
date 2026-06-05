import tempfile
import textwrap
from pathlib import Path

from src.workflow import get_workflow_execution_interval


def test_get_workflow_execution_interval_reads_01_workflow_hours() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        workflow_dir = Path(tmp_dir) / ".github" / "workflows"
        workflow_dir.mkdir(parents=True)
        (workflow_dir / "01.yml").write_text(
            textwrap.dedent(
                """
                name: test
                on:
                  schedule:
                    - cron: "0 */3 * * *"
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

        interval = get_workflow_execution_interval(workflow_dir / "01.yml")

        assert interval == "3 hours"


def test_get_workflow_execution_interval_supports_daily_schedule() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        workflow_dir = Path(tmp_dir) / ".github" / "workflows"
        workflow_dir.mkdir(parents=True)
        (workflow_dir / "01.yml").write_text(
            textwrap.dedent(
                """
                name: test
                on:
                  schedule:
                    - cron: "0 0 * * *"
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

        interval = get_workflow_execution_interval(workflow_dir / "01.yml")

        assert interval == "1 day"
