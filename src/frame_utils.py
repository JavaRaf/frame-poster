import random
import time
from pathlib import Path

import httpx
from PIL import Image
from tenacity import retry, stop_after_attempt, wait_exponential

from src.logger import get_logger

logger = get_logger(__name__)


client = httpx.Client(
    timeout=httpx.Timeout(30, connect=10),
    headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'})


def timestamp_to_frame(timestamp: str, fps: int | float = 3.5) -> int | None:
    """
    Converts a timestamp (H:MM:SS.CC) from .ass subtitle format to a frame number.
    Example: "0:01:02.50" → 1 minute, 2.5 seconds → calculated frame.

    Args:
        timestamp (str): Example: "0:01:02.50"
        fps (int, float): Frames per second. Example: 2

    Returns:
        int: Rounded frame number. Or None if error occurs.
    """
    try:
        hours, minutes, seconds = timestamp.split(":")
        seconds, centiseconds = seconds.split(".")
        total_seconds = (
            int(hours) * 3600
            + int(minutes) * 60
            + int(seconds)
            + int(centiseconds) / 100
        )
        return round(total_seconds * fps)
    except (ValueError, AttributeError) as error:
        logger.error("Invalid timestamp %r (expected H:MM:SS.CC): %s", timestamp, error)
        return None


def timestamp_to_seconds(time_str: str, format: str = "ass") -> float | None:
    """
    Converts a timestamp (H:MM:SS.CC) to total seconds (float).
    Example: "0:01:02.50" → 1 minute, 2.5 seconds → 62.5 seconds.

    Args:
        time_str (str): Example: "0:01:02.50"

    Returns:
        float: Total seconds. Or None if error occurs.
    """
    if format == "ass":

        try:
            h, m, s = time_str.split(":")
            s, cc = s.split(".")
            cc = cc.ljust(2, "0")  # ensure two digits
            total_seconds = (
                int(h) * 3600
                + int(m) * 60
                + int(s)
                + int(cc) / 100
            )
            return total_seconds
        except (ValueError, AttributeError) as error:
            logger.error("Invalid ASS timestamp %r: %s", time_str, error)
            return None

    elif format == "srt":

        try:
            hours, minutes, rest = time_str.split(":")
            seconds, millis = rest.split(",")
            total_seconds = (
                int(hours) * 3600
                + int(minutes) * 60
                + int(seconds)
                + int(millis) / 1000.0
            )
            return total_seconds
        except (ValueError, AttributeError) as error:
            logger.error("Invalid SRT timestamp %r: %s", time_str, error)
            return None

    else:
        # Not an exception, just a programming error, so skip exc_info.
        logger.error("Unsupported subtitle format %r (expected 'ass' or 'srt')", format)
        return None


def frame_to_timestamp(current_frame: int, img_fps: int | float) -> str | None:
    """Converts frame number to timestamp in .ass format (H:MM:SS.CC).

    Args:
        current_frame (int): Current frame number.
        img_fps (int | float): Frames per second of the video.

    Returns:
        str | None: Timestamp in the format 'H:MM:SS.CC', or None if error occurs.
    """

    try:
        total_seconds = current_frame / img_fps

        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        centiseconds = int(round((seconds % 1) * 100))
        seconds = int(seconds)

        # Rounding that can generate carry-over (ex: 59.999s -> 1:00.00)
        if centiseconds == 100:
            centiseconds = 0
            seconds += 1
            if seconds == 60:
                seconds = 0
                minutes += 1
                if minutes == 60:
                    minutes = 0
                    hours += 1
        return f"{int(hours)}:{int(minutes):02}:{int(seconds):02}.{centiseconds:02}"

    except (TypeError, ZeroDivisionError) as error:
        logger.error(
            "Failed to convert frame %r at fps=%r to timestamp: %s",
            current_frame, img_fps, error,
        )
        return None


def random_crop(frame_path: Path, configs: dict) -> tuple[Path, str] | None:
    """
    Returns a random crop of the frame.

    Args:
        frame_path: Path to the frame image.

    Returns:
        tuple[Path, str]: Tuple containing the path to the cropped image and the crop coordinates.
    """
    # These are type/state validations (not caught exceptions), so no exc_info.
    if not isinstance(frame_path, Path):
        logger.error("random_crop: frame_path must be a Path, got %s", type(frame_path).__name__)
        return None, None

    if not frame_path.is_file():
        logger.error("random_crop: file not found at %s", frame_path)
        return None, None

    try:
        # Keys describe the minimum and maximum *size* of the square crop in
        # pixels, not coordinates. The legacy ``min_x``/``min_y`` names are
        # still read as a fallback so older configs.yml files keep working.
        random_crop_cfg = configs.get("posting", {}).get("random_crop", {})
        min_size: int = random_crop_cfg.get("min_size", random_crop_cfg.get("min_x", 200))
        max_size: int = random_crop_cfg.get("max_size", random_crop_cfg.get("min_y", 600))

        crop_width = crop_height = random.randint(min_size, max_size)

        with Image.open(frame_path) as img:
            image_width, image_height = img.size

            if image_width < crop_width or image_height < crop_height:
                logger.error(
                    "Image %s (%dx%d) is smaller than requested crop (%dx%d)",
                    frame_path.name, image_width, image_height, crop_width, crop_height,
                )
                return None, None

            # Generate random crop coordinates
            crop_x = random.randint(0, image_width - crop_width)
            crop_y = random.randint(0, image_height - crop_height)

            # Crop image
            cropped_img = img.crop(
                (crop_x, crop_y, crop_x + crop_width, crop_y + crop_height)
            )

            # Save the cropped image
            cropped_path = (
                Path.cwd()
                / "temp"
                / f"cropped_frame{frame_path.suffix}"
            )
            cropped_path.parent.mkdir(exist_ok=True)

            cropped_img.save(cropped_path)
            message = (
                f"Random Crop. [{crop_width}x{crop_height} ~ X: {crop_x}, Y: {crop_y}]"
            )

            return cropped_path, message

    except (OSError, ValueError) as e:
        logger.error("Failed to crop %s: %s: %s", frame_path.name, type(e).__name__, e, exc_info=True)
        return None, None

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_frame(frame_number: int, episode_number: int, github_expects: dict) -> Path | None:
    """Download the frame from the github repository. and save it locally. 

    Args:
        frame_number (int): The frame number to download.
        episode_number (int): The episode number to download.
        github_expects (dict): The github expects.
    
    Returns:
        Path | None: The path to the downloaded frame, or None if error occurs.
    """


    # Short label reused across log lines so every message identifies the frame.
    frame_label = f"frame {frame_number} of episode {episode_number:02d}"

    username = github_expects.get("username")
    repo = github_expects.get("repo")
    branch = github_expects.get("branch")
    if not all([username, repo, branch]):
        logger.error("github config missing required keys (username/repo/branch): %r", github_expects)
        return None

    frame_url = (
        f"https://raw.githubusercontent.com/{username}/{repo}/{branch}/"
        f"{episode_number:02d}/{frame_number:04d}.jpg"
    )
    time.sleep(1)

    try:
        response = client.get(frame_url)

        # Raw.githubusercontent rate-limits aggressively; fall back to the
        # weserv proxy which serves the same file from a different origin.
        if response.status_code == 429:
            proxy_url = f"https://images.weserv.nl/?url={frame_url}"
            response = client.get(proxy_url)

        if response.status_code != 200:
            logger.error(
                "Failed to download %s: HTTP %s - %s",
                frame_label, response.status_code, response.text[:200],
            )
            # Let tenacity retry on rate limit; other statuses are not transient.
            if response.status_code == 429:
                response.raise_for_status()
            return None

        image_path = Path.cwd() / "images" / f"{episode_number:02d}" / f"{frame_number:04d}.jpg"
        image_path.parent.mkdir(parents=True, exist_ok=True)
        with image_path.open("wb") as f:
            f.write(response.content)
        return image_path

    except httpx.HTTPStatusError:
        # Already logged above; re-raise so tenacity can retry.
        raise
    except httpx.RequestError as e:
        logger.error("Network error while downloading %s: %s: %s", frame_label, type(e).__name__, e)
        return None