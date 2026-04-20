"""
poster module handles the coordination of posting operations to Facebook.

This module contains functions for posting frames, subtitles and random crops
to Facebook pages in an organized way.
"""

# Standard library imports
from pathlib import Path
from time import sleep

# Third party imports
from src.facebook import FacebookAPI
from src.frame_utils import random_crop
from src.logger import get_logger

# Initialize services
fb = FacebookAPI()
logger = get_logger(__name__)

def post_frame(message: str, frame_path: Path, placeholders: dict) -> str | None:
    """Post a frame and return the post ID."""
    # Small label used in log messages to pinpoint which frame/episode failed.
    frame_label = (
        f"frame {placeholders.get('frame_number')} "
        f"(episode {placeholders.get('episode_number')})"
    )
    try:
        post_id = fb.post_frame(message, frame_path)
        if post_id:
            print(
                f"├── season {placeholders.get('season_number')}, "
                f"episode {placeholders.get('episode_number')}, "
                f"frame {placeholders.get('frame_number')} out of {placeholders.get('max_frames')} has been posted", flush=True)
            sleep(2)
            return post_id
        logger.error("Facebook API returned no post id for %s", frame_label)
        return None
    except Exception as e:
        # Keep the exception type+message so the log is actionable
        # (e.g. HTTPStatusError vs ConnectError is very different).
        logger.error("Failed to post %s: %s: %s", frame_label, type(e).__name__, e, exc_info=True)
        return None


def post_subtitles(post_id: str, frame_number: int, episode_number: int, subtitle: str, configs: dict) -> str | None:
    """Post the subtitles associated with the frame."""
    if not configs.get("posting", {}).get("posting_subtitles", False):
        return None

    if not subtitle:
        return None

    context = f"subtitle for frame {frame_number} (episode {episode_number})"
    try:
        subtitle_post_id = fb.post_frame(subtitle, None, post_id)
        if subtitle_post_id:
            print("├── Subtitle has been posted", flush=True)
            sleep(2)
            return subtitle_post_id
        logger.error("Facebook API returned no post id for %s", context)
        return None
    except Exception as e:
        logger.error("Failed to post %s: %s: %s", context, type(e).__name__, e, exc_info=True)
        return None


def post_random_crop(post_id: str, frame_path: Path, configs: dict) -> str | None:
    """Post a random cropped frame."""
    if not configs.get("posting", {}).get("random_crop", {}).get("enabled", False):
        return None

    try:
        crop_path, crop_message = random_crop(frame_path, configs)
        # random_crop already logged the reason; just bail silently here.
        if not (crop_path and crop_message):
            return None

        crop_post_id = fb.post_frame(crop_message, crop_path, post_id)
        if crop_post_id:
            print("└── Random Crop has been posted", flush=True)
            sleep(2)
            return crop_post_id
        logger.error("Facebook API returned no post id for random crop of %s", frame_path.name)
        return None
    except Exception as e:
        logger.error(
            "Failed to post random crop of %s: %s: %s",
            frame_path.name, type(e).__name__, e, exc_info=True,
        )
        return None




