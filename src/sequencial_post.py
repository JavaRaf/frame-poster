import os
from pathlib import Path

from dotenv import load_dotenv
from ruamel.yaml import CommentedMap

from frame_utils import get_frame
from src.facebook import FacebookGraphAPI
from src.logger import get_logger
from src.subtitles import get_subtitle
from src.workflow import get_workflow_interval_hours

load_dotenv()


logger = get_logger(__name__)


def sequencial_post(facebook_client: FacebookGraphAPI, config: CommentedMap):
    # --- current progress ---
    progress_attr: CommentedMap = config.get("progress", {})
    current_season: int = progress_attr.get("season", 1)
    current_episode: int = progress_attr.get("episode", 1)

    # --- current season and episode data ---
    seasons_list: list = config.get("seasons", [])
    season_data = next((s for s in seasons_list if s.get("season") == current_season), {})
    episode_data = next(
        (ep for ep in season_data.get("episodes", []) if ep.get("episode") == current_episode),
        {},
    )

    if not episode_data:
        logger.error(f"Episode {current_episode} not found in season {current_season}")
        return

    # --- current posting configuration ---
    posting_config = config.get("posting", {})
    fph: int = posting_config.get("fph", 15)  # frames por hora
    post_interval: int = posting_config.get("post_interval", 2)  # minutos entre posts
    github_repo: str = config.get("github_repo", "")

    # --- Limits ---
    current_frame = max(1, progress_attr.get("frame", 0))  # garante mínimo 1
    stop_frame: int = current_frame + fph
    max_frames: int = episode_data.get("max_frames", 0)
    img_fps: int | float | None = episode_data.get("img_fps", None)



    # --- Static placeholders for post message formatting ---:
    # {season}, {episode}, {frame_number}, {max_frames}, {img_fps}, {fph},
    # {timestamp}, {subtitles}, {episode_title}, {post_interval}, {execution_interval}
    static_placeholders: dict = {
        "season"                : current_season,
        "episode"               : current_episode,
        "title"                 : episode_data.get("title", ""),
        "max_frames"            : max_frames,
        "img_fps"               : img_fps,
        "fph"                   : fph,
        "post_interval"         : post_interval,
        "execution_interval"    : get_workflow_interval_hours(),
    }

    # --- post loop ---
    for frame_number in range(current_frame, stop_frame + 1):
        if frame_number > max_frames:
            # TODO: atualizar progresso para o próximo episódio e salvar no config
            break

        # download frame
        frame_path = get_frame(current_season, current_episode, frame_number, github_repo)

        # Busca a legenda do frame
        subtitle_list = get_subtitle(current_season, current_episode, frame_number, img_fps)

        # TODO:
        # 1. buscar frame
        # 2. formatar a mensagem do post
        # 3. postar frame no facebook (unpublished)
        # 4. random_crop
        # 5. postar legenda no post criado
        # 6. publicar post
        # 7. atualizar progresso para o próximo frame e salvar no config

