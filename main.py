import os
import time
from pathlib import Path

from src.cli import parse_args
from src.console import print_header, print_separator
from src.facebook import FacebookAPI
from src.frame_utils import frame_to_timestamp, get_frame, end_episode_mov_next, update_config
from src.load_configs import load_and_validate
from src.logger import get_logger, log_post_id, set_log_timezone
from src.message import format_message
from src.poster import post_frame, post_random_crop, post_subtitles
from src.settings import CONFIGS_PATH, FB_TOKEN_ENV_VAR
from src.subtitles import get_subtitle_for_frame
from src.workflow import get_workflow_interval_hours


logger = get_logger(__name__) 


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    if args.fb_token:
        os.environ[FB_TOKEN_ENV_VAR] = args.fb_token.strip()

    config_path = Path(args.config_file) if args.config_file else CONFIGS_PATH
    config = load_and_validate(config_path)
    set_log_timezone(config.timezone)

    facebook_client = FacebookAPI(
        api_version=config.facebook.api_version,
        access_token=args.fb_token,
    )
    facebook_client.validate_token()
  

    episode_config = config.episodes[config.in_progress.episode]
    start_frame = config.in_progress.next_frame or 1
    last_frame = episode_config.max_frames + config.posting.fph + 1

    # Static placeholders that do not change between frames.
    static_placeholders = {
        "fph"                : config.posting.fph,
        "img_fps"            : episode_config.image_fps,
        "max_frames"         : episode_config.max_frames,
        "season_number"      : config.in_progress.season,
        "episode_title"      : episode_config.title,
        "episode_number"     : config.in_progress.episode,
        "posting_interval"   : config.posting.posting_interval,
        "execution_interval" : get_workflow_interval_hours(),
    }

    for frame_number in range(start_frame, last_frame):
        # Move to the next episode when the current one has finished.

        if end_episode_mov_next(frame_number, episode_config.max_frames, config):
            logger.info(
                "Episode %s completed; advancing to episode %s",
                config.in_progress.episode, config.in_progress.episode + 1,
            )
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
            "timestamp"    : frame_to_timestamp(frame_number, episode_config.image_fps),
            "subtitles"    : subtitle_text or "",
            "frame_number" : frame_number,
        }

        message = format_message(config.post_msg, placeholders)
        if not message:
            logger.error(
                "Aborting cycle: empty message after formatting for frame %s of episode %02d",
                frame_number, config.in_progress.episode,
            )

        # Publish the frame to Facebook.
        post_id = post_frame(facebook_client, message, frame_path, placeholders)
        if not post_id:
            logger.error(
                "Aborting cycle: frame %s of episode %02d was not posted",
                frame_number, config.in_progress.episode,
            )

        update_config(frame_number, config, episode_config)

        # Run follow-up publishing actions after the main post.
        facebook_client.repost_frame_to_album(message, frame_path, episode_config.album_id, config.posting.reposting_in_album)
        post_subtitles(facebook_client, post_id, frame_number, config.in_progress.episode, subtitle_text, config.posting.posting_subtitles)
        post_random_crop(facebook_client, post_id, frame_path, config.posting.random_crop.enabled, config.posting.random_crop.min_size, config.posting.random_crop.max_size)
        log_post_id(post_id, frame_number, config.in_progress.episode, config.in_progress.season, config.timezone)

        print_separator()
        time.sleep(config.posting.posting_interval * 5)  # 2 * 60 = 2 minutes

    # Update the Facebook bio with the final formatted message.
    bio_message = format_message(config.bio_msg, static_placeholders)
    if bio_message:
        facebook_client.update_bio(bio_message)

    end_summary()

    

    


if __name__ == "__main__":
    print_header("🚀 Starting the script")
    main()
    print_header("✅ Ending the script")
