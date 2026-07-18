import os
from pathlib import Path
from threading import Lock

import httpx
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.logger import get_logger
from src.settings import FB_TOKEN_ENV_VAR

logger = get_logger(__name__)


class FacebookAPIError(Exception):
    """Raised for unrecoverable Facebook Graph API failures."""


class FacebookAPI:
    """Thin client around the Facebook Graph API used by this project."""

    def __init__(self, api_version: str = "v21.0", access_token: str | None = None):
        self.base_url = f"https://graph.facebook.com/{api_version}"
        self.client = httpx.Client(
            base_url=self.base_url, timeout=httpx.Timeout(30, connect=10)
        )
        self.access_token = self._normalize_token(
            access_token or os.getenv(FB_TOKEN_ENV_VAR, "")
        )
        self._album_name_cache: dict[str, str | None] = {}
        self._album_name_cache_lock = Lock()

        if not self.access_token:
            logger.error("FB_TOKEN is not defined in the environment or passed by CLI")

    # -- lifecycle -----------------------------------------------------

    def __enter__(self) -> "FacebookAPI":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def close(self) -> None:
        self.client.close()

    # -- helpers ---------------------------------------------------------

    @staticmethod
    def _normalize_token(token: str | None) -> str | None:
        if not token:
            return None

        token = token.strip().removeprefix("FB_TOKEN=")
        return token or None

    @property
    def _auth_headers(self) -> dict[str, str]:
        """Authorization header used by all Graph API requests."""
        return {"Authorization": f"Bearer {self.access_token}"}

    @staticmethod
    def _truncate(text: str, limit: int = 500) -> str:
        return text[:limit]

    # -- public API --------------------------------------------------------

    def validate_token(self) -> tuple[bool, str]:
        """Validate the Facebook token.

        Returns:
            (True, "") when the token is valid.
            (False, reason) when the token is missing or the API call fails.
        """

        if not self.access_token:
            reason = f"{FB_TOKEN_ENV_VAR} is not defined in the environment"
            logger.error("%s", reason)
            return False, reason

        try:
            response = self.client.get("/me", headers=self._auth_headers)
            response.raise_for_status()
            return True, ""
        except httpx.HTTPStatusError as exc:
            reason = f"status_code {exc.response.status_code} {exc}"
            logger.error("Facebook token invalid or expired: %s", reason)
            return False, reason
        except httpx.HTTPError as exc:
            reason = f"{type(exc).__name__}: {exc}"
            logger.error("Facebook token invalid or expired: %s", reason)
            return False, reason

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    def _try_post(
        self, endpoint: str, params: dict, files: dict | None = None
    ) -> str | None:
        response = self.client.post(
            endpoint, params=params, files=files, headers=self._auth_headers
        )

        if response.status_code == 200:
            try:
                return response.json().get("id")
            except ValueError:
                logger.error(
                    "Facebook response was not valid JSON: %r",
                    self._truncate(response.text),
                )
                return None

        # Raising triggers tenacity's retry; the caller handles the final failure.
        response.raise_for_status()
        return None

    def post_frame(
        self,
        message: str = "",
        frame_path: Path | None = None,
        parent_id: str | None = None,
    ) -> str | None:
        """
        Posts a message (optionally with a photo) to Facebook, or as a
        comment on `parent_id` when provided.

        If all retry attempts fail, only logs the error and returns None.
        """
        endpoint = f"/{parent_id}/comments" if parent_id else "/me/photos"
        params = {"message": message}

        # Describe what we're posting so log lines pinpoint the failure.
        context = (
            f"comment on {parent_id}"
            if parent_id
            else (f"photo {frame_path.name}" if frame_path else "text post")
        )

        try:
            if not frame_path:
                return self._try_post(endpoint, params)

            with open(frame_path, "rb") as file:
                return self._try_post(endpoint, params, files={"source": file})
        except RetryError as e:
            logger.error("Failed to post %s after retries: %s", context, e)
            return None
        except OSError as e:
            logger.error("Failed to open frame %s: %s", frame_path, e)
            return None

    def update_bio(self, message: str) -> bool:
        """
        Updates the Facebook bio with the provided message.

        Args:
            message: The text to set as the bio. An empty string is a no-op.
        Returns:
            True if the bio was updated (or there was nothing to update),
            False otherwise.
        """

        if not message:
            logger.info("Bio message is empty, skipping bio update.")
            return True

        endpoint = "/me"
        params = {"about": message}

        try:
            response = self.client.post(
                endpoint, params=params, headers=self._auth_headers
            )
            if response.status_code == 200:
                return True
            # Body typically contains the Graph API error message (e.g.
            # expired token, missing permission). Truncate to avoid dumping
            # megabytes if something really weird comes back.
            logger.error(
                "Failed to update bio: HTTP %s - %s",
                response.status_code,
                self._truncate(response.text),
            )
            return False

        except httpx.HTTPError as e:
            logger.error("Failed to update bio: %s: %s", type(e).__name__, e)
            return False

    def album_name(self, album_id: str) -> str | None:
        """
        Get the name of an album, caching results per instance.
        Returns the album name if successful, otherwise None.
        """
        with self._album_name_cache_lock:
            if album_id in self._album_name_cache:
                return self._album_name_cache[album_id]

        name = self._fetch_album_name(album_id)

        with self._album_name_cache_lock:
            self._album_name_cache[album_id] = name
        return name

    def _fetch_album_name(self, album_id: str) -> str | None:
        try:
            endpoint = f"/{album_id}"
            params = {"fields": "name"}
            response = self.client.get(
                endpoint, params=params, headers=self._auth_headers
            )
            if response.status_code == 200:
                return response.json().get("name")
            logger.error(
                "Failed to get album name: HTTP %s - %s",
                response.status_code,
                self._truncate(response.text),
            )
            return None
        except httpx.HTTPError as e:
            logger.error("Failed to get album name: %s: %s", type(e).__name__, e)
            return None

    def repost_frame_to_album(
        self,
        message: str = "",
        frame_path: Path | None = None,
        album_id: str | None = None,
        resposting: dict | None = None,
    ) -> str | None:
        """
        Repost a frame to an album.
        Returns the post ID if successful, otherwise returns None.
        """

        if not resposting or not album_id:
            return None

        if not str(album_id).isdigit():
            logger.error(
                "Album repost is enabled but album_id %r is not a valid integer",
                album_id,
            )
            return None

        try:
            post_id = self.post_frame(message, frame_path, album_id)
        except RetryError as e:
            logger.error("Failed to repost to album %s after retries: %s", album_id, e)
            return None

        if not post_id:
            logger.error("Failed to repost frame to album %s", album_id)
            return None

        return post_id