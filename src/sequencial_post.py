import os
from pathlib import Path
from tabnanny import check

from dotenv import load_dotenv
from ruamel.yaml import CommentedMap

from src.frame_utils import get_frame, frame_to_timestamp
from src.facebook import FacebookGraphAPI
from src.logger import get_logger
from src.subtitles import get_subtitle
from src.workflow import get_workflow_interval_hours
from src.message import format_message
from src.poster import create_post, post_comment

load_dotenv()


logger = get_logger(__name__)


def sequencial_post(facebook_client: FacebookGraphAPI, config: CommentedMap):
    # --- current progress ---
    progress_attr            : CommentedMap = config.get("progress", {})
    current_season           : int = progress_attr.get("season", 1)
    current_episode          : int = progress_attr.get("episode", 1)

    # --- current season and episode data ---
    seasons_list             : list = config.get("seasons", [])
    season_data              : dict = next((s for s in seasons_list if s.get("season") == current_season), {})
    episode_data             : dict = next(
        (ep for ep in season_data.get("episodes", []) if ep.get("episode") == current_episode),
        {},
    )

    if not episode_data:
        logger.error(f"Episode {current_episode} not found in season {current_season}")
        return

    # --- current posting configuration ---
    posting_config           : dict = config.get("posting", {})
    fph                      : int = posting_config.get("fph", 15)  # frames por hora
    post_interval            : int = posting_config.get("post_interval", 2)  # minutos entre posts
    github_repo              : str = episode_data.get("github_repo", "")
    sub_comment_enabled      : bool = config.get("sub_comment", False)

    TEMPLATE_POST_MSG        : str = config.get("TEMPLATE_POST_MSG")
    TEMPLATE_BIO_MSG         : str = config.get("TEMPLATE_BIO_MSG")

    # --- Limits ---
    current_frame            : int = max(1, progress_attr.get("frame", 0))  # garante mínimo 1
    stop_frame               : int = current_frame + fph
    max_frames               : int = episode_data.get("max_frames", 0)
    img_fps                  : int | float | None = episode_data.get("img_fps", None)

    # --- Random crop ---
    random_crop              : dict = config.get("random_crop", {})

    random_crop_enabled      : bool = random_crop.get("enabled", False)
    min_size                 : int  = random_crop.get("min_size")
    max_size                 : int  = random_crop.get("max_size")
    
    




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
        if not frame_path:
            logger.error(
                "Failed to get frame %d for episode %d (github_repo: %s) - check if frame exists",
                frame_number, current_episode, github_repo
            )
            break

        # Busca a legenda do frame
        subtitle_list = get_subtitle(current_season, current_episode, frame_number, img_fps)

        # extendendo os placeholders estáticos com os dinâmicos
        placeholders: dict = {
            **static_placeholders,
            "frame_number"  : frame_number,
            "subtitles"     : subtitle_list,
            "timestamp"     : frame_to_timestamp(frame_number, img_fps) or "{}"
        }

        # foramtando a mensagem que acompanha a imagem
        template_post_msg = format_message(TEMPLATE_POST_MSG, placeholders)
        if not template_post_msg:
            logger.error("Template post message is empty: episode %s, frame %s", current_episode, frame_number)
            break
        
        post_id = create_post(facebook_client, frame_path, template_post_msg, current_episode, frame_number)
        if not post_id:
            break

        post_comment(facebook_client, post_id, subtitle_list, sub_comment_enabled)
            

        # TODO:
        # comment_id = post_comment(facebook_client, post_id, template_post_msg, placeholders)
        # random_id = random_crop(frame_path, random_crop_width, random_crop_height)

        # make_post_public(frame_path, template_post_msg, placeholders)
        # save_progress(current_season, current_episode, frame_number)

        # respost_id  = album_repost()
        

        

