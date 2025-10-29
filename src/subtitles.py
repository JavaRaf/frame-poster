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

@lru_cache(maxsize=32)
def parse_srt_file(file_path: Path) -> dict:
    """
    Reads and parses an .srt subtitle file into a normalized structure.

    The .srt format is composed of blocks:
      1) numeric index
      2) time range line: "HH:MM:SS,mmm --> HH:MM:SS,mmm"
      3) one or more text lines
      4) blank line

    Returns a dict with metadata and a list of items containing Start/End in seconds.
    """

    with file_path.open("r", encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f]

    time_line_regex = re.compile(r"^(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})$")

    subtitles_data: list[dict] = []
    collected_text_lines: list[str] = []
    language_name = "Unknown"

    i = 0
    while i < len(lines):
        # Skip empty lines
        if lines[i].strip() == "":
            i += 1
            continue

        # Optional numeric index line
        if lines[i].strip().isdigit():
            i += 1
            if i >= len(lines):
                break

        # Time line must be present now
        match = time_line_regex.match(lines[i])
        if not match:
            # Not a valid block; advance to next line
            i += 1
            continue

        start_ts, end_ts = match.groups()
        i += 1

        # Collect one or more text lines until blank line or EOF
        text_lines: list[str] = []
        while i < len(lines) and lines[i].strip() != "":
            text_lines.append(lines[i])
            i += 1

        # Prepare entry
        text = remove_tags(" ".join(text_lines).strip())
        try:
            start_seconds = timestamp_to_seconds(start_ts, format="srt")
            end_seconds = timestamp_to_seconds(end_ts, format="srt")
        except Exception as error:
            logger.error(f"Error parsing SRT timestamps '{start_ts}' -> '{end_ts}': {error}", exc_info=True)
            i += 1
            continue

        subtitles_data.append({
            "Start": start_seconds,
            "End": end_seconds,
            "Text": text,

            # these are not used for srt subtitles
            "Style": None,
            "Actor": None,
            "MarginL": None,
            "MarginR": None,
            "MarginV": None,
            "Effect": None,
        })

        collected_text_lines.extend(text_lines)

        # Move past the blank line separator if present
        if i < len(lines) and lines[i].strip() == "":
            i += 1

    # Language detection from collected text
    try:
        language_name = LANGUAGE_CODES.get(detect(" ".join(collected_text_lines)), "Unknown")
    except Exception:
        language_name = "Unknown"

    return {
        "file_name": file_path.name,
        "language": language_name,
        "subtitles": subtitles_data,
    }


def __ass_format(frame_number: int, img_fps: float, subtitles_data: dict) -> str | None:
    """
    Returns the formatted text of the active subtitle for the current frame.
    """
    time = frame_number / img_fps # frame_number in seconds

    # regex patterns for signs
    SIGN_EXPRESSION = re.compile(
        r"sign|signs",
        re.IGNORECASE,
    )
    # regex patterns for music
    EXPRESSION_MUSIC = re.compile(
        r"\blyric(s)?\b|\bsong(s)?\b|\bopening\b|\bending\b|\bop\b|\bed\b",
        re.IGNORECASE,
    )

    for sub in subtitles_data.get("subtitles", []):
        if sub["Start"] <= time <= sub["End"]:
            style = (sub.get("Style") or "")
            actor = (sub.get("Actor") or "")
            text = sub.get("Text", "")
            lang = subtitles_data.get("language", "")

            if SIGN_EXPRESSION.search(style) or SIGN_EXPRESSION.search(actor):
                text = f"【 {text} 】"
            elif EXPRESSION_MUSIC.search(style) or EXPRESSION_MUSIC.search(actor):
                text = f"♪ {text} ♪\n"

            return f"[{lang}]\n{text}" if text else None

    return None

def __srt_format(frame_number: int, img_fps: float, subtitles_data: dict) -> str | None:
    """Returns the active SRT subtitle text for the current frame.

    SRT entries contain only timing and text; we simply prefix with language
    and return the text for the active time window if present.
    """
    current_time = frame_number / img_fps
    lang = subtitles_data.get("language", "")
    for sub in subtitles_data.get("subtitles", []):
        if sub["Start"] <= current_time <= sub["End"]:
            text = sub.get("Text", "")
            return f"[{lang}]\n{text}" if text else None
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
                srt_subtitles_data = parse_srt_file(subtitle_file)
                formatted_message = __srt_format(frame_number, image_fps, srt_subtitles_data)
            case _:
                formatted_message = None

        if formatted_message:
            formatted_messages += formatted_message + "\n\n"

    return formatted_messages or None





