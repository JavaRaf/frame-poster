import os
import time
from pathlib import Path

from src.cli import parse_args
from src.console import console, print_header, print_separator
from src.facebook import FacebookAPI
from src.frame_utils import frame_to_timestamp, get_frame
from src.load_configs import load_and_validate, save_configs
from src.logger import get_logger, log_post_id, set_log_timezone
from src.message import format_message
from src.poster import post_frame, post_random_crop, post_subtitles
from src.settings import CONFIGS_PATH, FB_TOKEN_ENV_VAR
from src.subtitles import get_subtitle_for_frame
from src.summary_step import Status, add_summary_row, start_summary, end_summary
from src.variable_check import check_fb_token
from src.workflow import get_workflow_interval_hours


logger = get_logger(__name__) 


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    if args.fb_token:
        os.environ[FB_TOKEN_ENV_VAR] = args.fb_token.strip()

    # ── Summary table wraps the entire execution ───────────────────────
    start_summary()
    check_fb_token()

    # Temporary client just for token validation (default api_version is fine).
    if not FacebookAPI(access_token=args.fb_token).validate_token():
        logger.error("Aborting run: Facebook token is invalid or missing.")
        add_summary_row("Final status", "Aborted — invalid token", Status.ERROR)
        end_summary()
        return
    # ────────────────────────────────────────────────────────────────────

    config_path = Path(args.config_file) if args.config_file else CONFIGS_PATH
    config = load_and_validate(config_path)
    set_log_timezone(config.timezone)

    facebook_client = FacebookAPI(
        api_version=config.facebook.api_version,
        access_token=args.fb_token,
    )

    episode_config = config.episodes[config.in_progress.episode]
    last_frame_to_post = config.in_progress.frame + config.posting.fph

    # Static placeholders that do not change between frames.
    static_placeholders = {
        "fph"                : config.posting.fph,
        "img_fps"            : episode_config.image_fps,
        "episode_title"      : episode_config.title,
        "episode_number"     : config.in_progress.episode,
        "max_frames"         : episode_config.max_frames,
        "season_number"      : config.in_progress.season,
        "execution_interval" : get_workflow_interval_hours(),
        "posting_interval"   : config.posting.posting_interval,
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
            save_configs(config.model_dump(), config_path)
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
            "frame_number" : frame_number,
            "timestamp"    : frame_to_timestamp(frame_number, episode_config.image_fps),
            "subtitles"    : subtitle_text or "",
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

        # Save progress after a successful post.
        config.in_progress.frame = frame_number
        current_config_snapshot = config.model_dump()
        save_configs(current_config_snapshot, config_path)

        # Run follow-up publishing actions after the main post.
        facebook_client.repost_frame_to_album(message, frame_path, episode_config.album_id, current_config_snapshot)
        post_subtitles(facebook_client, post_id, frame_number, config.in_progress.episode, subtitle_text, current_config_snapshot)
        post_random_crop(facebook_client, post_id, frame_path, current_config_snapshot)
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
