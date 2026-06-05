import time

from src.frame_utils import frame_to_timestamp, get_frame
from src.load_configs import load_and_validate, save_configs
from src.logger import get_logger
from src.message import format_message
from src.poster import fb, post_frame, post_random_crop, post_subtitles
from src.subtitles import get_subtitle_for_frame
from src.workflow import get_workflow_execution_interval

logger = get_logger(__name__)




def main():
    if not fb.validate_token():
        logger.error("Aborting run: Facebook token is invalid or missing.")
        return

    config = load_and_validate()
    ep_cfg = config.episodes[config.in_progress.episode]
    last_frame = config.in_progress.frame + config.posting.fph

    # ── placeholders estáticos (não mudam entre frames) ───────────
    static_placeholders = {
        "season_number": config.in_progress.season,
        "episode_number": config.in_progress.episode,
        "episode_title": ep_cfg.title,
        "max_frames": ep_cfg.max_frames,
        "img_fps": ep_cfg.image_fps,
        "fph": config.posting.fph,
        "execution_interval": get_workflow_execution_interval(),
        "posting_interval": config.posting.posting_interval,
    }

    for frame_number in range(config.in_progress.frame + 1, last_frame + 1):
        # ── avançar para o próximo episódio se este acabou ──
        if frame_number > ep_cfg.max_frames:
            logger.info(
                "Episode %s completed; advancing to episode %s",
                config.in_progress.episode,
                config.in_progress.episode + 1,
            )
            config.in_progress.episode += 1
            config.in_progress.frame = 0
            save_configs(config.model_dump())
            break

        # ── baixar o frame ──
        frame_path = get_frame(frame_number, config.in_progress.episode, config.github.model_dump())
        if not frame_path:
            logger.error(
                "Aborting cycle: could not download frame %s of episode %02d",
                frame_number, config.in_progress.episode,
            )
            break

        # ── obter legenda ──
        subtitles = get_subtitle_for_frame(frame_number, config.in_progress.episode, ep_cfg.image_fps)

        # ── montar placeholders e formatar mensagem ──
        placeholders = {
            **static_placeholders,
            "frame_number": frame_number,
            "timestamp": frame_to_timestamp(frame_number, ep_cfg.image_fps),
            "subtitles": subtitles or "",
        }
        message = format_message(config.post_msg, placeholders)
        if not message:
            logger.error(
                "Aborting cycle: empty message after formatting for frame %s of episode %02d",
                frame_number, config.in_progress.episode,
            )
            break

        # ── postar o frame ──
        post_id = post_frame(message, frame_path, placeholders)
        if not post_id:
            logger.error(
                "Aborting cycle: frame %s of episode %02d was not posted",
                frame_number, config.in_progress.episode,
            )
            break

        # ── persistir progresso ──
        config.in_progress.frame = frame_number
        raw_config = config.model_dump()
        save_configs(raw_config)

        # ── acções pós-post ──
        fb.repost_frame_to_album(message, frame_path, ep_cfg.album_id, raw_config)
        post_subtitles(post_id, frame_number, config.in_progress.episode, subtitles, raw_config)
        post_random_crop(post_id, frame_path, raw_config)
        fb.save_fb_log(post_id, frame_number, config.in_progress.episode)

        print(f"{'-' * 50}\n\n")
        time.sleep(config.posting.posting_interval * 60)

    # ── actualizar biografia ──
    bio_message = format_message(config.bio_msg, static_placeholders)
    fb.update_bio(bio_message)
    

    



    
    


    



if __name__ == "__main__":
    print('\n' + '-' * 50 + '\n' "Starting the script" + '\n' + '-' * 50 + "\n\n",  flush=True) # makes visualization better in CI/CD environments
    main()
    print('\n' + '-' * 50 + '\n' "Ending the script" + '\n' + '-' * 50 +"\n\n",  flush=True) # makes visualization better in CI/CD environments
