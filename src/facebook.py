import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.logger import get_logger

logger = get_logger(__name__)
FB_LOG_PATH = Path.cwd() / "logs" / "fb_log.txt"
FB_LOG_PATH.touch(exist_ok=True)

# Loads environment variables from the .env file. Existing OS-level variables
# take precedence (useful in CI/CD where secrets come from the runner).
load_dotenv(".env")


class FacebookAPI:
    def __init__(self, api_version: str = "v21.0"):
        token = os.getenv("FB_TOKEN")
        if not token:
            # Raising surfaces the problem at startup instead of on the first
            # request; no need to also log here because the stack trace is clear.
            raise ValueError("FB_TOKEN is not defined in the environment")

        self.base_url = f"https://graph.facebook.com/{api_version}"

        # Defensive cleanup: tokens pasted from CI/CD sometimes come with a
        # stray "FB_TOKEN=" prefix or trailing whitespace/newlines.
        token = token.strip().removeprefix("FB_TOKEN=")
        self.access_token = token
        self.client = httpx.Client(base_url=self.base_url, timeout=httpx.Timeout(30, connect=10))


    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    def _try_post(self, endpoint: str, params: dict, files: dict = None) -> str | None:
        response = self.client.post(endpoint, params=params, files=files)

        if response.status_code == 200:
            try:
                return response.json().get("id")
            except ValueError:
                logger.error("Facebook response was not valid JSON: %r", response.text[:500])
                return None

        # Raising triggers tenacity's retry; the caller handles the final failure.
        response.raise_for_status()
        return None

    def _log_post_failure(self, context: str, error: RetryError) -> None:
        """Log the root cause hidden inside a tenacity ``RetryError``.

        Without this, all we'd see is ``RetryError: Failed to post after
        multiple attempts`` and we'd lose the actual Graph API payload (which
        usually has a very clear message, e.g. "Error validating access token").
        """
        last_exc = error.last_attempt.exception() if error.last_attempt else None
        if isinstance(last_exc, httpx.HTTPStatusError):
            response = last_exc.response
            logger.error(
                "Failed to post %s after retries: HTTP %s - %s",
                context, response.status_code, response.text[:500],
            )
        else:
            logger.error("Failed to post %s after retries: %s", context, last_exc, exc_info=True)

    def post_frame(self, message: str = "", frame_path: Path = None, parent_id: str = None) -> str | None:
        """
        Posts a message to Facebook.
        If all attempts fail, only logs the error and returns None.
        """
        endpoint = (
            f"{self.base_url}/{parent_id}/comments"
            if parent_id
            else f"{self.base_url}/me/photos"
        )
        params = {"access_token": self.access_token, "message": message}

        # Describe what we're posting so log lines pinpoint the failure.
        context = (
            f"comment on {parent_id}" if parent_id
            else (f"photo {frame_path.name}" if frame_path else "text post")
        )

        if not frame_path:
            try:
                return self._try_post(endpoint, params)
            except RetryError as e:
                self._log_post_failure(context, e)
                return None

        with open(frame_path, "rb") as file:
            files = {"source": file}
            try:
                return self._try_post(endpoint, params, files)
            except RetryError as e:
                self._log_post_failure(context, e)
                return None

    


    def save_fb_log(self, post_id: str, frame: int, episode: int) -> None:
        """
        Saves the post ID in a format https://facebook.com/{id} creating a direct link to the post
        Args:
            post_id (str): The ID of the post
            frame (int): The frame number
            episode (int): The episode number
        Returns:
            None
        """
        try:
            with FB_LOG_PATH.open("a", encoding="utf-8") as file:
                file.write(f"frame {frame}, episode {episode} - https://facebook.com/{post_id}\n")
        except OSError as e:
            logger.error("Failed to append to fb log (%s): %s", FB_LOG_PATH, e, exc_info=True)



    def update_bio(self, message: str) -> bool:
        """
        Updates the Facebook bio with the provided message.
        The message can be formatted with placeholders.
        Args:
            message (str): The message to update the bio with
        Returns:
            bool: True if the bio was updated successfully, False otherwise
        """
        endpoint = f"{self.base_url}/me"
        params = {"access_token": self.access_token, "about": message}

        try:
            response = self.client.post(endpoint, params=params)
            if response.status_code == 200:
                return True
            # Body typically contains the Graph API error message (e.g.
            # expired token, missing permission). Truncate to avoid dumping
            # megabytes if something really weird comes back.
            logger.error(
                "Failed to update bio: HTTP %s - %s",
                response.status_code, response.text[:500],
            )
            return False

        except httpx.HTTPError as e:
            logger.error("Failed to update bio: %s: %s", type(e).__name__, e, exc_info=True)
            return False



    def repost_frame_to_album(self, message: str = "", frame_path: Path = None, album_id: str = None, configs: dict = None) -> str | None:
        """
        Repost a frame to an album.
        Returns the post ID if successful, otherwise returns None.
        """

        reposting_to_album = configs.get("posting", {}).get("reposting_in_album", False)

        if not reposting_to_album:
            return None

        if not album_id:
            return None
        
        if not str(album_id).isdigit():
            logger.error(
                "Album repost is enabled but album_id %r is not a valid integer",
                album_id,
            )
            return None

        try:
            print(f"├── Reposting frame to album {album_id}...", flush=True)
            return self.post_frame(message, frame_path, album_id)
        except RetryError as e:
            self._log_post_failure(f"album repost to {album_id}", e)
            return None

        

    