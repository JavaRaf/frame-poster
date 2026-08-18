"""
Custom validation for config.yml that works with ruamel.yaml CommentedMap.
Preserves the CommentedMap format while providing validation.
"""

from ruamel.yaml.comments import CommentedMap
from src.logger import get_logger

logger = get_logger(__name__)


def validate_config(config: CommentedMap) -> None:
    """
    Validate the entire config structure.

    Args:
        config: The CommentedMap loaded from config.yml

    """

    # Validate top-level required fields
    required_fields = {
        "progress": dict,
        "seasons": list,
        "TEMPLATE_POST_MSG": str,
        "TEMPLATE_BIO_MSG": str,
        "TEMPLATE_RANDOM_FRAME_MSG": str,
        "posting": dict,
        "random_crop": dict,
    }

    for field, expected_type in required_fields.items():
        if field not in config:
            logger.error(f"Missing required field: '{field}'")
        elif not isinstance(config[field], expected_type):
            logger.error(
                f"Field '{field}' must be {expected_type.__name__}, got {type(config[field]).__name__}"
            )

    # Validate progress section
    if "progress" in config:
        _validate_progress(config["progress"])

    # Validate seasons section
    if "seasons" in config:
        _validate_seasons(config["seasons"])

    # Validate posting section
    if "posting" in config:
        _validate_posting(config["posting"])

    # Validate random_crop section
    if "random_crop" in config:
        _validate_random_crop(config["random_crop"])

    # Validate optional fields with defaults
    if "facebook_api_version" in config and not isinstance(config["facebook_api_version"], str):
        logger.error(
            f"Field 'facebook_api_version' must be str, got {type(config['facebook_api_version']).__name__}"
        )

    if "timezone" in config and not isinstance(config["timezone"], int):
        logger.error(f"Field 'timezone' must be int, got {type(config['timezone']).__name__}")


def _validate_progress(progress: CommentedMap) -> None:
    """Validate progress section."""

    required = {
        "season": int,
        "episode": int,
        "frame": int,
    }

    for field, expected_type in required.items():
        if field not in progress:
            logger.error(f"Missing required field in progress: '{field}'")
        elif not isinstance(progress[field], expected_type):
            logger.error(
                f"Field 'progress.{field}' must be {expected_type.__name__}, got {type(progress[field]).__name__}"
            )

    if "frame" in progress and progress["frame"] < 0:
        logger.error("Field 'progress.frame' must be >= 0")


def _validate_seasons(seasons: list) -> None:
    """Validate seasons section."""

    if not seasons:
        logger.error("Field 'seasons' cannot be empty")

    for i, season in enumerate(seasons):
        if not isinstance(season, dict):
            logger.error(f"Season {i} must be a dict, got {type(season).__name__}")
            continue

        # Validate season fields
        if "season" not in season:
            logger.error(f"Season {i}: missing required field 'season'")
        elif not isinstance(season["season"], (str, int)):
            logger.error(
                f"Season {i}: field 'season' must be str or int, got {type(season['season']).__name__}"
            )

        # Validate base_link (optional)
        if "base_link" in season and not isinstance(season["base_link"], str):
            logger.error(
                f"Season {i}: field 'base_link' must be str, got {type(season['base_link']).__name__}"
            )

        # Validate episodes
        if "episodes" not in season:
            logger.error(f"Season {i}: missing required field 'episodes'")
        elif not isinstance(season["episodes"], list):
            logger.error(
                f"Season {i}: field 'episodes' must be list, got {type(season['episodes']).__name__}"
            )
        else:
            _validate_episodes(season["episodes"], i)


def _validate_episodes(episodes: list, season_index: int) -> None:
    """Validate episodes within a season."""

    if not episodes:
        logger.error(f"Season {season_index}: episodes list cannot be empty")

    for i, episode in enumerate(episodes):
        if not isinstance(episode, dict):
            logger.error(f"episode {i}: must be a dict, got {type(episode).__name__}")
            continue

        # Required fields
        required = {
            "episode": (str, int),
            "max_frames": int,
            "github_repo": str,
        }

        for field, expected_types in required.items():
            # Normalize to tuple if single type
            if not isinstance(expected_types, tuple):
                expected_types = (expected_types,)

            if field not in episode:
                logger.error(
                    f"season [{season_index}].episode index [{i}]: missing required field '{field}'"
                )
            elif not isinstance(episode[field], expected_types):
                type_name = " or ".join(t.__name__ for t in expected_types)
                logger.error(
                    f"season [{season_index}].episode index [{i}]: field '{field}' must be {type_name}, got {type(episode[field]).__name__}"
                )

        # Optional fields
        if (
            "title" in episode
            and episode["title"] is not None
            and not isinstance(episode["title"], str)
        ):
            logger.error(
                f"episode {i}: field 'title' must be str or None, got {type(episode['title']).__name__}"
            )

        if "album_id" in episode and episode["album_id"] is not None:
            if not isinstance(episode["album_id"], (str, int)):
                logger.error(
                    f"season [{season_index}].episode index [{i}]: field 'album_id' must be str, int, or None, got {type(episode['album_id']).__name__}"
                )

        if "github_repo" in episode and not isinstance(episode["github_repo"], str):
            logger.error(
                f"season [{season_index}].episode index [{i}]: field 'github_repo' must be str, got {type(episode['github_repo']).__name__}"
            )

        # Validate values
        if "img_fps" in episode:
            img_fps = episode["img_fps"]

            if img_fps is not None and img_fps != "":
                if not isinstance(img_fps, (int, float)):
                    logger.error(
                        f"season [{season_index}].episode index [{i}]: field 'img_fps' must be int or float, got {type(img_fps).__name__}"
                    )
                elif img_fps <= 0:
                    logger.error(
                        f"season [{season_index}].episode index [{i}]: field 'img_fps' must be > 0"
                    )

        if "max_frames" in episode:
            max_frames = episode["max_frames"]
            if isinstance(max_frames, int) and max_frames < 0:
                logger.error(
                    f"season [{season_index}].episode index [{i}]: field 'max_frames' must be >= 0"
                )


def _validate_posting(posting: CommentedMap) -> None:
    """Validate posting section."""

    required = {
        "fph": int,
        "post_interval": int,
        "sub_comment": bool,
        "album_repost": bool,
        "random_post": bool,
    }

    for field, expected_type in required.items():
        if field not in posting:
            logger.error(f"Missing required field in posting: '{field}'")
        elif not isinstance(posting[field], expected_type):
            logger.error(
                f"Field 'posting.{field}' must be {expected_type.__name__}, got {type(posting[field]).__name__}"
            )

    # Validate values
    if "fph" in posting and isinstance(posting["fph"], int) and posting["fph"] < 1:
        logger.error("Field 'posting.fph' must be >= 1")

    if (
        "post_interval" in posting
        and isinstance(posting["post_interval"], int)
        and posting["post_interval"] < 1
    ):
        logger.error("Field 'posting.post_interval' must be >= 1")


def _validate_random_crop(random_crop: CommentedMap) -> None:
    """Validate random_crop section."""

    required = {
        "enabled": bool,
        "min_size": int,
        "max_size": int,
    }

    for field, expected_type in required.items():
        if field not in random_crop:
            logger.error(f"Missing required field in random_crop: '{field}'")
        elif not isinstance(random_crop[field], expected_type):
            logger.error(
                f"Field 'random_crop.{field}' must be {expected_type.__name__}, got {type(random_crop[field]).__name__}"
            )

    # Validate values
    if "min_size" in random_crop and random_crop["min_size"] < 1:
        logger.error("Field 'random_crop.min_size' must be >= 1")

    if "max_size" in random_crop and random_crop["max_size"] < 1:
        logger.error("Field 'random_crop.max_size' must be >= 1")

    if "min_size" in random_crop and "max_size" in random_crop:
        if random_crop["min_size"] > random_crop["max_size"]:
            logger.error("Field 'random_crop.min_size' must be <= random_crop.max_size")
