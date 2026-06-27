import os
import re
from pathlib import Path
from functools import lru_cache

import httpx
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.logger import get_logger
from src.settings import FB_LOG_PATH, FB_TOKEN_ENV_VAR

logger = get_logger(__name__)
FB_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
FB_LOG_PATH.touch(exist_ok=True)
TOKEN_RE = re.compile(r"(?i)(access_token(?:%3D|=))([^&\s]+)")


def sanitize_for_logging(value: object) -> str:
    """Redact Facebook access tokens from exception strings and URLs."""
    return TOKEN_RE.sub(r"\1[REDACTED]", "" if value is None else str(value))

class FacebookAPI:
    def __init__(self, api_version: str = "v21.0", access_token: str | None = None):
        self.base_url = f"https://graph.facebook.com/{api_version}"
        self.client = httpx.Client(base_url=self.base_url, timeout=httpx.Timeout(30, connect=10))
        self.access_token = self._normalize_token(
            access_token
            or os.getenv(FB_TOKEN_ENV_VAR, "")
        )

        if not self.access_token:
            logger.error("FB_TOKEN is not defined in the environment or passed by CLI")

    def _normalize_token(self, token: str | None) -> str | None:
        if not token:
            return None

        token = token.strip().removeprefix("FB_TOKEN=")
        return token if token else None


    def validate_token(self) -> bool:
        """Return True only when the configured Facebook token is valid."""
        token = self.access_token or os.getenv(FB_TOKEN_ENV_VAR, "").strip().removeprefix("FB_TOKEN=")
        if not token:
            logger.error("%s is not defined in the environment", FB_TOKEN_ENV_VAR)
            return False

        try:
            response = httpx.get(
                f"{self.base_url}/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            logger.error(
                "Facebook token validation failed: %s: %s",
                type(exc).__name__,
                sanitize_for_logging(exc),
            )
            return False


    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    def _try_post(self, endpoint: str, params: dict, files: dict = None) -> str | None:
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = self.client.post(endpoint, params=params, files=files, headers=headers)

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
                context,
                response.status_code,
                response.text[:500],
            )
        else:
            logger.error("Failed to post %s after retries: %s", context, sanitize_for_logging(last_exc))

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
        params = {"message": message}

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

        if message == "":
            logger.info("Bio message is empty, skipping bio update.")
            return True
        
        endpoint = f"{self.base_url}/me"
        params = {"about": message}
        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            response = self.client.post(endpoint, params=params, headers=headers)
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
            logger.error("Failed to update bio: %s: %s", type(e).__name__, sanitize_for_logging(e))
            return False


    @lru_cache(maxsize=128)
    def album_name(self, album_id: str) -> str | None:
        """
        Get the name of an album.
        Returns the album name if successful, otherwise returns None.
        """

        try:
            endpoint = f"{self.base_url}/{album_id}"
            params = {"fields": "name"}
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = self.client.get(endpoint, params=params, headers=headers)
            if response.status_code == 200:
                return response.json().get("name")
            logger.error(
                "Failed to get album name: HTTP %s - %s",
                response.status_code, response.text[:500],
            )
            return None
        except httpx.HTTPError as e:
            logger.error("Failed to get album name: %s: %s", type(e).__name__, sanitize_for_logging(e))
            return None
        


    def repost_frame_to_album(self, message: str = "", frame_path: Path = None, album_id: str = None, configs: dict = None) -> str | None:
        """
        Repost a frame to an album.
        Returns the post ID if successful, otherwise returns None.
        """

        reposting_to_album = configs.get("posting", {}).get("reposting_in_album", False)

        if not reposting_to_album or not album_id:
            return None
        
        if not str(album_id).isdigit():
            logger.error(
                "Album repost is enabled but album_id %r is not a valid integer",
                album_id,
            )
            return None

        try:
            id = self.post_frame(message, frame_path, album_id)
            if not id:
                logger.error(f'Failed to repost frame to album {album_id}', flush=True)
                return None

            print(f'├── Frame reposted to album "{self.album_name(album_id)}" with id "{id}" ', flush=True)
            return id

        except RetryError as e:
            self._log_post_failure(f"album repost to {album_id}", e)
            return None


    