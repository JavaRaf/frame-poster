import re
from functools import lru_cache
from src.logger import get_logger
from pathlib import Path
from src.frame_utils import timestamp_to_seconds
from langdetect import detect




logger = get_logger(__name__)


LANGUAGE_CODES = {
    "en": "English",
    "pt": "Português",
    "es": "Español",
    "spa": "Español",
    "ja": "日本語",
    "ko": "한국어",
    "zh-cn": "简体中文",
    "zh-tw": "繁體中文",
    "fr": "Français",
    "de": "Deutsch",
    "it": "Italiano",
    "ru": "Русский",
    "tr": "Türkçe",
    "vi": "Tiếng Việt",
    "nl": "Nederlands",
    "uk": "Українська",
    "id": "Bahasa Indonesia",
    "tl": "Tagalog",
    # add more language codes here
}




def remove_tags(message: str) -> str:
    """Remove ASS/SSA tags and control codes from a subtitle string."""
    if not message or not isinstance(message, str):
        return message
        
    pattern = re.compile(r"\{\s*[^}]*\s*\}|\\N|\\[a-zA-Z]+\d*|\\c&H[0-9A-Fa-f]+&")
    message = pattern.sub(" ", message)
    return re.sub(r"\s+", " ", message).strip()



@lru_cache(maxsize=32)
def parse_subtitle_file(file_path: Path) -> dict:
    """
    Reads and parses a .ass subtitle file, returning subtitle information and detected language.
    Uses cache to avoid parsing the same file multiple times.

    Args:
        file_path (Path): Path to the .ass subtitle file.

    Returns:
        dict: Dictionary containing file name, detected language, and a list of subtitle entries.
    """

    # Open the subtitle file and collect all lines that start with "Dialogue:"
    with file_path.open("r", encoding="utf-8") as f:
        dialogues = [line for line in f if line.startswith("Dialogue:")]

    # Concatenate all dialogue texts (with tags removed) for language detection
    dialogues_text = " ".join(remove_tags(line.split(",", 9)[9]) for line in dialogues)
    try:
        # Detect language using langdetect and map to human-readable name
        language_name = LANGUAGE_CODES.get(detect(dialogues_text), "Unknown")
    except Exception:
        language_name = "Unknown"

    subtitles_data = []
    for line in dialogues:
        try:
            # Split the dialogue line into its respective fields
            parts = line.split(",", 9)
            subtitles_data.append({
                "Layer": parts[0],
                "Start": timestamp_to_seconds(parts[1]),
                "End": timestamp_to_seconds(parts[2]),
                "Style": parts[3],
                "Actor": parts[4],
                "MarginL": parts[5],
                "MarginR": parts[6],
                "MarginV": parts[7],
                "Effect": parts[8],
                "Text": remove_tags(parts[9]),
            })
        except Exception as error:
            # Log error if parsing a line fails, but continue processing the rest
            logger.error(f"Error while parsing line {line}: {error}", exc_info=True)
            continue

    return {
        "file": file_path.name,
        "language": language_name,
        "subtitles": subtitles_data
    }


        


