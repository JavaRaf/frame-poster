import os

from src.facebook import FacebookGraphAPI, ApiVersion
from ruamel.yaml import CommentedMap

from src.logger import get_logger

from src.load_configs import load_and_validate

from dotenv import load_dotenv

from pathlib import Path

from src.subtitles import get_subtitle

load_dotenv()


logger = get_logger(__name__)


def sequencial_post(facebook_client: FacebookGraphAPI, config: CommentedMap):

    progress_attr: CommentedMap = config.get("progress", {})
    current_season: int = progress_attr.get("season", 1)
    current_episode: int = progress_attr.get("episode", 1)

    seasons_list: list = config.get("seasons", [])

    season_data = next((s for s in seasons_list if s.get("season") == current_season), {})
    episodes_list = season_data.get("episodes", [])

    episode_data = next(
        (episode for episode in episodes_list if episode.get("episode") == current_episode), {}
    )

    if not episode_data:
        logger.error(f"Episode {current_episode} not found in season {current_season}")
        return

    fph: int = config.get("posting", {}).get(
        "fph", 15
    )  # frames per hour: how many frames to post in this run (default 15)
    current_frame = max(1, progress_attr.get("frame", 0))  # ensure at least 1
    stop_frame: int = current_frame + fph  # calculate stop frame
    max_frames: int = episode_data.get("max_frames", 0)  # get max frames for this episode
    img_fps: int | float = episode_data.get("img_fps", 3.5)  # get image fps for this episode

    for frame in range(current_frame, stop_frame + 1):
        if frame > max_frames:
            # TODO: update progress to next episode and save to config
            break

        # TODO:
        # 1. buscar frame
        # 2. legenda
        subtitle_list = get_subtitle(
            current_season,
            current_episode,
            frame,
            img_fps
        )


        # 3. formatar a mensgem do post
        # 4. postar frame no facebook (unpublished)
        # 5. random_crop
        # 6. postar legenda no post criado
        # 7. (publish post)
        # 8. update progress to next frame and save to config


# for test
if __name__ == "__main__":
    config: CommentedMap = load_and_validate()
    facebook_client = FacebookGraphAPI(os.getenv("FB_TOKEN"), api_version=ApiVersion.V25_0)
    sequencial_post(facebook_client, config)
