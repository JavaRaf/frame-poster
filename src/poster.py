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
from src.console import DynamicTable
from src.frame_utils import random_crop
from src.logger import get_logger

logger = get_logger(__name__)


def post_frame(
    facebook: FacebookAPI, message: str, frame_path: Path, placeholders: dict
) -> str | None:
    """Post a frame and return the post ID."""
    # Small label used in log messages to pinpoint which frame/episode failed.
    frame_label = (
        f"frame {placeholders.get('frame_number')} "
        f"(episode {placeholders.get('episode_number')})"
    )
    try:
        post_id = facebook.post_frame(message, frame_path)
        if post_id:
            (
                DynamicTable()
                .add("Season", str(placeholders.get("season_number")))
                .add("Episode", str(placeholders.get("episode_number")))
                .add("Frame", f"{placeholders.get('frame_number')} / {placeholders.get('max_frames')}")
                .print()
            )
            sleep(2)
            return post_id
        logger.error("Facebook API returned no post id for %s", frame_label)
        return None
    except Exception as e:
        # Keep the exception type+message so the log is actionable
        # (e.g. HTTPStatusError vs ConnectError is very different).
        logger.error(
            "Failed to post %s: %s: %s",
            frame_label,
            type(e).__name__,
            e,
        )
        return None


def post_subtitles(
    facebook: FacebookAPI,
    post_id: str,
    frame_number: int,
    episode_number: int,
    subtitle: str,
    posting_subtitles: bool,
) -> str | None:
    """Post the subtitles associated with the frame."""
    if not posting_subtitles:
        return None

    if not subtitle:
        return None

    context = f"subtitle for frame {frame_number} (episode {episode_number})"
    try:
        subtitle_post_id = facebook.post_frame(subtitle, None, post_id)
        if subtitle_post_id:
            DynamicTable().add("Subtitle", "posted").print()
            sleep(2)
            return subtitle_post_id
        logger.error("Facebook API returned no post id for %s", context)
        return None
    except Exception as e:
        logger.error(
            "Failed to post %s: %s: %s",
            context,
            type(e).__name__,
            e,
        )
        return None


def post_random_crop(
    facebook: FacebookAPI, post_id: str, frame_path: Path, random_crop_enabled: bool, random_crop_min_size: int, random_crop_max_size: int
) -> str | None:
    """Post a random cropped frame."""
    if not random_crop_enabled:
        return None

    try:
        crop_path, crop_message = random_crop(frame_path, random_crop_min_size, random_crop_max_size)
        # random_crop already logged the reason; just bail silently here.
        if not (crop_path and crop_message):
            return None

        crop_post_id = facebook.post_frame(crop_message, crop_path, post_id)
        if crop_post_id:
            DynamicTable().add("Random Crop", "posted").print()
            sleep(2)
            return crop_post_id
        logger.error(
            "Facebook API returned no post id for random crop of %s", frame_path.name
        )
        return None
    except Exception as e:
        logger.error(
            "Failed to post random crop of %s: %s: %s",
            frame_path.name,
            type(e).__name__,
            e,
        )
        return None


def repost_frame_into_album(
    facebook: FacebookAPI, message: str, frame_path: str, album_id: str, respost: bool
) -> bool:
    """Repost a frame into an album."""

    response = facebook.repost_frame_to_album(message, frame_path, album_id, respost)

    if response is None:
        return False

    (
        DynamicTable()
        .add("Repost", f'Album "{facebook.album_name(album_id)}"')
        .add("Post ID", response)
        .print()
    )
