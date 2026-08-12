from src.logger import get_logger

logger = get_logger(__name__)


class SafeDict(dict):
    def __missing__(self, key):
        return f"{{{key}}}"


def format_message(message: str | None, placeholders: dict) -> str:
    """
    Formata mensagem de forma segura, sem lançar exceção
    se um placeholder não existir.
    """
    if message is None:
        logger.error("format_message received None as message template")
        return ""

    return message.format_map(SafeDict(placeholders))
