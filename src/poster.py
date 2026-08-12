from pathlib import Path
from src.logger import get_logger
from src.facebook import FacebookGraphAPI

logger = get_logger(__name__)


def create_post(
    facebook_client: FacebookGraphAPI,
    frame_path: Path,
    message: str,
    current_episode: int,
    frame_number: int,
) -> str | None:
    """Upload photo and create unpublished post in sequence.

    Args:
        facebook_client: Facebook API client.
        frame_path: Path to the image file.
        message: Post message.
        current_episode: Current episode number for logging.
        frame_number: Frame number for logging.

    Returns:
        Post ID if successful, None otherwise.
    """
    photo_id = facebook_client.upload_photo(frame_path, message)
    if not photo_id:
        logger.error(
            "Failed to upload photo: episode %s, frame %s",
            current_episode,
            frame_number,
        )
        return None

    post_id = facebook_client.create_unpublished_post(message, photo_id)
    if not post_id:
        logger.error(
            "Failed to create post: episode %s, frame %s", current_episode, frame_number
        )
        return None

    return post_id


def post_comment(
    facebook_client: FacebookGraphAPI,
    post_id: str,
    subtitles: list[dict[str, str]],
    sub_comment_enabled: bool,
):
    if not sub_comment_enabled:
        return

    if not subtitles:
        return

    comments = []
    english_comment = None

    for sub_dict in subtitles:
        lang = sub_dict.get("lang")
        text = sub_dict.get("text")
        comment = f"[{lang}]\n{text}\n\n"

        if lang == "English":
            english_comment = comment
        else:
            comments.append(comment)

    # Put English comment first
    if english_comment:
        comments.insert(0, english_comment)

    try:
        facebook_client.comments_post(post_id, "".join(comments))
    except Exception as e:
        logger.error("Failed to post comment: %s", e)


def post_random_crop():
    pass


def album_repost():
    pass


def make_post_public(post_id: str):
    pass
