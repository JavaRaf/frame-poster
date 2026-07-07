"""
Pydantic models for validating the structure of ``configs.yml``.

Usage::

    from src.load_configs import load_configs
    from src.config_models import AppConfig

    raw = load_configs()
    config = AppConfig.model_validate(raw)
"""

from __future__ import annotations

from typing import Optional, Union

from pydantic import BaseModel, Field, model_validator


class GitHubConfig(BaseModel):
    """Represents the ``github:`` section of the config."""

    username: str
    repo: str
    branch: str = "main"


class InProgressConfig(BaseModel):
    """Represents the ``in_progress:`` section — tracks where we left off."""

    season: int = Field(default=1, ge=1)
    episode: int = Field(default=1, ge=1)
    frame: int = Field(default=0, ge=0)


class RandomCropConfig(BaseModel):
    """Settings for the random-crop feature posted as a comment."""

    enabled: bool = True
    min_size: int = Field(default=200, ge=1)
    max_size: int = Field(default=600, ge=1)

    @model_validator(mode="after")
    def _ensure_min_lte_max(self) -> "RandomCropConfig":
        if self.min_size > self.max_size:
            raise ValueError(
                f"random_crop.min_size ({self.min_size}) must be <= "
                f"random_crop.max_size ({self.max_size})"
            )
        return self


class PostingConfig(BaseModel):
    """Represents the ``posting:`` section of the config."""

    fph: int = Field(default=15, ge=1)
    posting_interval: int = Field(default=2, ge=1)
    posting_subtitles: bool = True
    reposting_in_album: bool = True
    random_crop: RandomCropConfig = RandomCropConfig()


class EpisodeConfig(BaseModel):
    """Settings for a single episode under the ``episodes:`` mapping."""

    title: Optional[str] = None
    image_fps: float = Field(default=3.5, gt=0)
    max_frames: int = Field(default=0, ge=0)
    album_id: Optional[Union[int, str]] = None


class FacebookConfig(BaseModel):
    """Represents the ``facebook:`` section of the config."""

    api_version: str = "v21.0"


class AppConfig(BaseModel):
    """Top-level validated representation of ``configs.yml``."""

    github: GitHubConfig
    facebook: FacebookConfig = FacebookConfig()
    in_progress: InProgressConfig = InProgressConfig()
    episodes: dict[int, EpisodeConfig] = {}
    posting: PostingConfig = PostingConfig()
    post_msg: str = ""
    bio_msg: str = ""

    @model_validator(mode="before")
    @classmethod
    def _drop_empty_episodes(cls, data: dict) -> dict:
        """Remove episode entries that are ``None`` (key with no value in YAML)."""
        episodes = data.get("episodes", {})
        if isinstance(episodes, dict):
            data["episodes"] = {k: v for k, v in episodes.items() if v is not None}
        return data

    @model_validator(mode="after")
    def _ensure_current_episode_exists(self) -> "AppConfig":
        """Fail early if ``in_progress.episode`` isn't defined in ``episodes:``."""
        ep = self.in_progress.episode
        if ep not in self.episodes:
            raise ValueError(
                f"in_progress.episode is set to {ep}, but no entry exists for "
                f"episode {ep} in the 'episodes:' section of configs.yml"
            )
        return self
