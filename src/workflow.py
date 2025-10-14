import os
from src.logger import get_logger

logger = get_logger(__name__)


def get_workflow_execution_interval() -> str:
    """
    Obtém o intervalo de execução do workflow do arquivo YAML.

    Returns:
        str: Intervalo em horas formatado com dois dígitos
    """
    try:
        workflow_files = os.listdir(".github/workflows")
        for workflow_file in workflow_files:
            if workflow_file.endswith(".yml") or workflow_file.endswith(".yaml"):
                with open(f".github/workflows/{workflow_file}", "r") as file:
                    for line in file:
                        if line.strip().startswith("- cron:"):
                            cron_expression = line.split("cron:")[1].strip().strip('"')
                            parts = cron_expression.split()
                            if len(parts) == 5 and parts[1].startswith("*/"):
                                execution_interval = int(parts[1].replace("*/", ""))
                                return f"{execution_interval}"
        return "0"
    except Exception as e:
        logger.error(f"Erro ao ler intervalo de execução: {e}", exc_info=True)
        return "0"