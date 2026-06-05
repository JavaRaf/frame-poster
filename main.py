import time

from src.frame_utils import frame_to_timestamp, get_frame
from src.load_configs import load_and_validate, save_configs
from src.logger import get_logger
from src.message import format_message
from src.poster import fb, post_frame, post_random_crop, post_subtitles
from src.subtitles import get_subtitle_for_frame
from src.workflow import get_workflow_execution_interval

logger = get_logger(__name__)



def main() -> None:
    """Run the posting cycle for the current episode and frame range."""
    if not fb.validate_token():
        logger.error("Aborting run: Facebook token is invalid or missing.")
        return

    config = load_and_validate()
    episode_config = config.episodes[config.in_progress.episode]
    last_frame_to_post = config.in_progress.frame + config.posting.fph

    # Static placeholders that do not change between frames.
    static_placeholders = {
        "season_number": config.in_progress.season,
        "episode_number": config.in_progress.episode,
        "episode_title": episode_config.title,
        "max_frames": episode_config.max_frames,
        "img_fps": episode_config.image_fps,
        "fph": config.posting.fph,
        "execution_interval": get_workflow_execution_interval(),
        "posting_interval": config.posting.posting_interval,
    }

    for frame_number in range(config.in_progress.frame + 1, last_frame_to_post + 1):
        # Move to the next episode when the current one has finished.
        if frame_number > episode_config.max_frames:
            logger.info(
                "Episode %s completed; advancing to episode %s",
                config.in_progress.episode,
                config.in_progress.episode + 1,
            )
            config.in_progress.episode += 1
            config.in_progress.frame = 0
            save_configs(config.model_dump())
            break

        # Download the next frame image for posting.
        frame_path = get_frame(frame_number, config.in_progress.episode, config.github.model_dump())
        if not frame_path:
            logger.error(
                "Aborting cycle: could not download frame %s of episode %02d",
                frame_number, config.in_progress.episode,
            )
            break

        # Retrieve the subtitle line for the current frame.
        subtitle_text = get_subtitle_for_frame(frame_number, config.in_progress.episode, episode_config.image_fps)

        # Build the dynamic placeholders and format the post message.
        placeholders = {
            **static_placeholders,
            "frame_number": frame_number,
            "timestamp": frame_to_timestamp(frame_number, episode_config.image_fps),
            "subtitles": subtitle_text or "",
        }
        message = format_message(config.post_msg, placeholders)
        if not message:
            logger.error(
                "Aborting cycle: empty message after formatting for frame %s of episode %02d",
                frame_number, config.in_progress.episode,
            )
            break

        # Publish the frame to Facebook.
        post_id = post_frame(message, frame_path, placeholders)
        if not post_id:
            logger.error(
                "Aborting cycle: frame %s of episode %02d was not posted",
                frame_number, config.in_progress.episode,
            )
            break

        # Save progress after a successful post.
        config.in_progress.frame = frame_number
        current_config_snapshot = config.model_dump()
        save_configs(current_config_snapshot)

        # Run follow-up publishing actions after the main post.
        fb.repost_frame_to_album(message, frame_path, episode_config.album_id, current_config_snapshot)
        post_subtitles(post_id, frame_number, config.in_progress.episode, subtitle_text, current_config_snapshot)
        post_random_crop(post_id, frame_path, current_config_snapshot)
        fb.save_fb_log(post_id, frame_number, config.in_progress.episode)

        print(f"{'-' * 50}\n\n")
        time.sleep(config.posting.posting_interval * 60)

    # Update the Facebook bio with the final formatted message.
    bio_message = format_message(config.bio_msg, static_placeholders)
    fb.update_bio(bio_message)
    

    


if __name__ == "__main__":
    print('\n' + '-' * 50 + '\n' "Starting the script" + '\n' + '-' * 50 + "\n\n", flush=True)
    main()
    print('\n' + '-' * 50 + '\n' "Ending the script" + '\n' + '-' * 50 + "\n\n", flush=True)
