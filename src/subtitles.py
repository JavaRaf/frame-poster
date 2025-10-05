import re
from src.logger import get_logger



logger = get_logger(__name__)







def remove_tags(message: str) -> str:
    """Remove ASS/SSA tags and control codes from a subtitle string."""
    if not message or not isinstance(message, str):
        return message
        
    pattern = re.compile(r"\{\s*[^}]*\s*\}|\\N|\\[a-zA-Z]+\d*|\\c&H[0-9A-Fa-f]+&")
    message = pattern.sub(" ", message)
    return re.sub(r"\s+", " ", message).strip()
