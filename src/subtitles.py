import re
from functools import lru_cache
from pathlib import Path

import httpx
from langdetect import detect
from tenacity import retry, stop_after_attempt, wait_exponential

from src.frame_utils import timestamp_to_seconds
from src.logger import get_logger

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
def parse_ass_file(file_path: Path) -> dict:
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
        "file_name": file_path.name,
        "language": language_name,
        "subtitles": subtitles_data
    }

def parse_srt_file(file_path: Path) -> dict:
    pass

def __ass_format(frame_number: int, img_fps: float, subtitles_data: dict) -> str | None:
    """
    Returns the formatted text of the active subtitle for the current frame.
    """
    time = frame_number / img_fps # frame_number in seconds

    for sub in subtitles_data.get("subtitles", []):
        if sub["Start"] <= time <= sub["End"]:
            style = (sub.get("Style") or "").lower()
            actor = (sub.get("Actor") or "").lower()
            text = sub.get("Text", "")

            if style.startswith("sign") or actor.startswith("sign"):
                text = f"【 {text} 】"
            elif "lyric" in style or "song" in style or "lyric" in actor or "song" in actor:
                text = f"♪ {text} ♪\n"

            return f"[{subtitles_data.get('language', '')}]\n{text}"

    return None

def get_subtitle_for_frame(frame_number: int, episode_number: int, image_fps: (int | float)) -> str | None:
    """
    Returns formatted subtitle messages for a given frame and episode.

    Args:
        frame_number (int): The frame number to retrieve subtitles for.
        episode_number (int): The episode number to look up subtitle files.
        image_fps (int | float): The frames per second of the image/video.
    Returns:
        str | None: The formatted subtitle messages, or None if not found.
    """
    
    if not isinstance(frame_number, int) or not isinstance(episode_number, int):
        logger.error("Error, frame_number and episode_number must be integers.")
        return None

    subtitles_root_folder = Path("subtitles")
    episode_subtitles_folder = subtitles_root_folder / f"{episode_number:02d}"

    if not episode_subtitles_folder.exists() or not episode_subtitles_folder.is_dir():
        logger.error(f"Episode subtitles folder '{episode_subtitles_folder}' not found.")
        return None

    subtitle_files = [subtitle_file for subtitle_file in episode_subtitles_folder.iterdir() if subtitle_file.is_file()]
    if not subtitle_files:
        logger.error(f"No subtitle files found in folder '{episode_subtitles_folder}'.")
        return None

    formatted_messages = ""
    for subtitle_file in subtitle_files:
        match subtitle_file.suffix:
            case ".ass":
                ass_subtitles_data = parse_ass_file(subtitle_file)
                formatted_message = __ass_format(frame_number, image_fps, ass_subtitles_data)
            case ".srt":
                formatted_message = None
            case _:
                formatted_message = None

        if formatted_message:
            formatted_messages += formatted_message + "\n\n"

    return formatted_messages or None





