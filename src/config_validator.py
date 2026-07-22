"""
Custom validation for config.yml that works with ruamel.yaml CommentedMap.
Preserves the CommentedMap format while providing validation.
"""

from ruamel.yaml.comments import CommentedMap
from typing import Any, get_type_hints
from src.logger import get_logger

logger = get_logger(__name__)  


class ValidationError(Exception):
    """Custom validation error with detailed message."""
    pass


def validate_config(config: CommentedMap) -> None:
    """
    Validate the entire config structure.
    
    Args:
        config: The CommentedMap loaded from config.yml
        
    Raises:
        ValidationError: If validation fails with detailed error message
    """
    errors = []
    
    # Validate top-level required fields
    required_fields = {
        'progress': dict,
        'seasons': list,
        'TEMPLATE_POST_MSG': str,
        'TEMPLATE_BIO_MSG': str,
        'TEMPLATE_RANDOM_FRAME_MSG': str,
        'posting': dict,
        'random_crop': dict,
    }
    
    for field, expected_type in required_fields.items():
        if field not in config:
            errors.append(f"Missing required field: '{field}'")
        elif not isinstance(config[field], expected_type):
            errors.append(f"Field '{field}' must be {expected_type.__name__}, got {type(config[field]).__name__}")
    
    
    # Validate progress section
    if 'progress' in config:
        progress_errors = _validate_progress(config['progress'])
        errors.extend(progress_errors)
    
    # Validate seasons section
    if 'seasons' in config:
        seasons_errors = _validate_seasons(config['seasons'])
        errors.extend(seasons_errors)
    
    # Validate posting section
    if 'posting' in config:
        posting_errors = _validate_posting(config['posting'])
        errors.extend(posting_errors)
    
    # Validate random_crop section
    if 'random_crop' in config:
        crop_errors = _validate_random_crop(config['random_crop'])
        errors.extend(crop_errors)
    
    # Validate optional fields with defaults
    if 'facebook_api_version' in config and not isinstance(config['facebook_api_version'], str):
        errors.append(f"Field 'facebook_api_version' must be str, got {type(config['facebook_api_version']).__name__}")
    
    if 'timezone' in config and not isinstance(config['timezone'], int):
        errors.append(f"Field 'timezone' must be int, got {type(config['timezone']).__name__}")
    
    if errors:
        for error in errors:
            logger.error(error)
        raise ValidationError("\n".join(errors))




def _validate_progress(progress: CommentedMap) -> list[str]:
    """Validate progress section."""
    errors = []
    
    required = {
        'season': int,
        'episode': int,
        'frame': int,
    }
    
    for field, expected_type in required.items():
        if field not in progress:
            errors.append(f"Missing required field in progress: '{field}'")
        elif not isinstance(progress[field], expected_type):
            errors.append(f"Field 'progress.{field}' must be {expected_type.__name__}, got {type(progress[field]).__name__}")
    

    if 'frame' in progress and progress['frame'] < 0:
        errors.append("Field 'progress.frame' must be >= 0")
    
    return errors


def _validate_seasons(seasons: list) -> list[str]:
    """Validate seasons section."""
    errors = []
    
    if not seasons:
        errors.append("Field 'seasons' cannot be empty")
        return errors
    
    for i, season in enumerate(seasons):
        if not isinstance(season, dict):
            errors.append(f"Season {i} must be a dict, got {type(season).__name__}")
            continue
        
        # Validate season fields
        if 'season' not in season:
            errors.append(f"Season {i}: missing required field 'season'")
        elif not isinstance(season['season'], (str, int)):
            errors.append(f"Season {i}: field 'season' must be str or int, got {type(season['season']).__name__}")
        
        # Validate base_link (optional)
        if 'base_link' in season and not isinstance(season['base_link'], str):
            errors.append(f"Season {i}: field 'base_link' must be str, got {type(season['base_link']).__name__}")
        
        # Validate episodes
        if 'episodes' not in season:
            errors.append(f"Season {i}: missing required field 'episodes'")
        elif not isinstance(season['episodes'], list):
            errors.append(f"Season {i}: field 'episodes' must be list, got {type(season['episodes']).__name__}")
        else:
            episode_errors = _validate_episodes(season['episodes'], i)
            errors.extend(episode_errors)
    
    return errors


def _validate_episodes(episodes: list, season_index: int) -> list[str]:
    """Validate episodes within a season."""
    errors = []
    
    if not episodes:
        errors.append(f"Season {season_index}: episodes list cannot be empty")
        return errors
    
    for i, episode in enumerate(episodes):
        if not isinstance(episode, dict):
            errors.append(f"episode {i}: must be a dict, got {type(episode).__name__}")
            continue
        
        # Required fields
        required = {
            'episode': (str, int),
            'image_fps': (int, float),
            'max_frames': int,
        }
        
        for field, expected_types in required.items():
            # Normalize to tuple if single type
            if not isinstance(expected_types, tuple):
                expected_types = (expected_types,)
            
            if field not in episode:
                errors.append(f"season [{season_index}].episode index [{i}]: missing required field '{field}'")
            elif not isinstance(episode[field], expected_types):
                type_name = " or ".join(t.__name__ for t in expected_types)
                errors.append(f"season [{season_index}].episode index [{i}]: field '{field}' must be {type_name}, got {type(episode[field]).__name__}")
        
        # Optional fields
        if 'title' in episode and episode['title'] is not None and not isinstance(episode['title'], str):
            errors.append(f"episode {i}: field 'title' must be str or None, got {type(episode['title']).__name__}")
        
        if 'album_id' in episode and episode['album_id'] is not None:
            if not isinstance(episode['album_id'], (str, int)):
                errors.append(f"season [{season_index}].episode index [{i}]: field 'album_id' must be str, int, or None, got {type(episode['album_id']).__name__}")
        
        if 'github_repo' in episode and not isinstance(episode['github_repo'], str):
            errors.append(f"season [{season_index}].episode index [{i}]: field 'github_repo' must be str, got {type(episode['github_repo']).__name__}")
        
        # Validate values
        if 'image_fps' in episode and episode['image_fps'] <= 0:
            errors.append(f"season [{season_index}].episode index [{i}]: field 'image_fps' must be > 0")
        
        if 'max_frames' in episode and episode['max_frames'] < 0:
            errors.append(f"season [{season_index}].episode index [{i}]: field 'max_frames' must be >= 0")
    
    return errors


def _validate_posting(posting: CommentedMap) -> list[str]:
    """Validate posting section."""
    errors = []
    
    required = {
        'fph': int,
        'post_interval': int,
        'subcomment': bool,
        'album_repost': bool,
    }
    
    for field, expected_type in required.items():
        if field not in posting:
            errors.append(f"Missing required field in posting: '{field}'")
        elif not isinstance(posting[field], expected_type):
            errors.append(f"Field 'posting.{field}' must be {expected_type.__name__}, got {type(posting[field]).__name__}")
    
    # Validate values
    if 'fph' in posting and isinstance(posting['fph'], int) and posting['fph'] < 1:
        errors.append("Field 'posting.fph' must be >= 1")
    
    if 'post_interval' in posting and isinstance(posting['post_interval'], int) and posting['post_interval'] < 1:
        errors.append("Field 'posting.post_interval' must be >= 1")

    return errors


def _validate_random_crop(random_crop: CommentedMap) -> list[str]:
    """Validate random_crop section."""
    errors = []
    
    required = {
        'enabled': bool,
        'min_size': int,
        'max_size': int,
    }
    
    for field, expected_type in required.items():
        if field not in random_crop:
            errors.append(f"Missing required field in random_crop: '{field}'")
        elif not isinstance(random_crop[field], expected_type):
            errors.append(f"Field 'random_crop.{field}' must be {expected_type.__name__}, got {type(random_crop[field]).__name__}")
    
    # Validate values
    if 'min_size' in random_crop and random_crop['min_size'] < 1:
        errors.append("Field 'random_crop.min_size' must be >= 1")
    
    if 'max_size' in random_crop and random_crop['max_size'] < 1:
        errors.append("Field 'random_crop.max_size' must be >= 1")
    
    if 'min_size' in random_crop and 'max_size' in random_crop:
        if random_crop['min_size'] > random_crop['max_size']:
            errors.append("Field 'random_crop.min_size' must be <= random_crop.max_size")
    
    return errors
