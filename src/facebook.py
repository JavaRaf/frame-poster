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

#-------------------------------- new class --------------------------------------


from enum import Enum
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


class ApiVersion(str, Enum):
    """Supported Graph API versions. Update when Facebook launches
    or deprecates versions (https://developers.facebook.com/docs/graph-api/changelog)."""

    V20_0 = "v20.0"
    V21_0 = "v21.0"
    V22_0 = "v22.0"
    V23_0 = "v23.0"
    V24_0 = "v24.0"
    V25_0 = "v25.0"


class FacebookGraphAPI:
    def __init__(
        self,
        access_token: str,
        api_version: ApiVersion = ApiVersion.V25_0,
    ):
        self.access_token = self._normalize_token(access_token)
        self.api_version = api_version
        self.client = httpx.Client(
            base_url=f"https://graph.facebook.com/{api_version.value}",
            timeout=httpx.Timeout(30, connect=10),
        )
        self._album_name_cache: dict[str, str | None] = {}
        self._album_name_cache_lock = Lock()

        if not self.access_token:
            logger.error("%s is not defined or is invalid", FB_TOKEN_ENV_VAR)

    def __enter__(self) -> "FacebookGraphAPI":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def close(self) -> None:
        self.client.close()

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

    @staticmethod
    def _normalize_token(token: str | None) -> str | None:
        if not token:
            return None

        # remove the FB_TOKEN prefix if present
        token = token.strip().removeprefix("FB_TOKEN=")
        return token or None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    def validate_token(self) -> tuple[bool, str]:
        """Validate the Facebook token.

        Returns:
            (True, "") when the token is valid.
            (False, reason) when the token is missing or the call fails.
        """
        if not self.access_token:
            reason = f"{FB_TOKEN_ENV_VAR} is not defined in the environment"
            logger.error("%s", reason)
            return False, reason

        try:
            response = self.client.get("/me", headers=self._headers)
            response.raise_for_status()
            return True, response.text

        except RetryError as exc:
            reason = str(exc)
            logger.error("Facebook token invalid or expired after attempts: %s", reason)
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
    def upload_photo(
        self,
        frame_path: Path,
        message: str = "",
        album_id: str | None = None,
        published: bool = False,
    ) -> str | None:
        """Upload a photo to Facebook.

        Args:
            frame_path: Path to the image.
            message: Optional message for the photo.
            album_id: Optional album ID.
            published: If True, publishes the photo directly.

        Returns:
            Photo ID or None on error.
        """
        endpoint = f"/{album_id}/photos" if album_id else "/me/photos"
        params = {"published": str(published).lower()}
        if message:
            params["message"] = message

        try:
            with frame_path.open("rb") as image:
                response = self.client.post(
                    endpoint,
                    params=params,
                    files={"source": image},
                    headers=self._headers,
                )
                response.raise_for_status()
                try:
                    photo_id = response.json().get("id")
                    return photo_id
                except ValueError:
                    logger.error("invalid response from API: %s", response.text)
                    return None

        except httpx.HTTPError as e:
            logger.error("error uploading photo %s: %s", frame_path, e)
            raise
        except OSError as e:
            logger.error("error opening file %s: %s", frame_path, e)
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    def create_unpublished_post(self, message: str, photo_id: str) -> str | None:
        """Create a draft (unpublished) post referencing an already uploaded photo."""
        payload = {
            "message": message,
            "attached_media": [{"media_fbid": photo_id}],
            "published": "false",
        }
        try:
            response = self.client.post("/me/feed", json=payload, headers=self._headers)
            response.raise_for_status()
            post_id = response.json().get("id")
            return post_id
        except httpx.HTTPError as e:
            logger.error("Failed to create draft post after attempts: %s", e)
            return None
        except ValueError:
            logger.error("invalid response from API: %s", response.text)
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    def publish_post(self, post_id: str) -> bool:
        """Publish a post previously created as a draft."""
        try:
            response = self.client.post(
                f"/{post_id}", params={"is_published": "true"}, headers=self._headers
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.error("Failed to publish post %s after attempts: %s", post_id, e)
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    def comments_post(
        self, post_id: str, message: str, frame_path: Path | None = None
    ) -> str | None:
        """Comment on a post.

        Args:
            post_id: ID of the post to comment on.
            message: Comment text.
            frame_path: Optional path to an image attached to the comment.

        Returns:
            True if the comment was created successfully, False otherwise.
        """
        try:
            if frame_path:
                with frame_path.open("rb") as f:
                    response = self.client.post(
                        f"/{post_id}/comments",
                        data={"message": message},
                        files={"source": f},
                        headers=self._headers,
                    )
            else:
                response = self.client.post(
                    f"/{post_id}/comments",
                    params={"message": message},
                    headers=self._headers,
                )

            response.raise_for_status()
            comment_id = response.json().get("id")

            return comment_id

        except httpx.HTTPError as e:
            logger.error("Failed to post comment after attempts: %s", e)
            return False
        except OSError as e:
            logger.error("Failed to open image %s: %s", frame_path, e)
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    def update_bio(self, message: str) -> bool:
        """Update the Facebook bio.

        Args:
            message: New bio message.

        Returns:
            True if updated successfully, False otherwise.
        """
        if not message:
            logger.info("Bio message is empty, skipping update.")
            return True

        try:
            response = self.client.post("/me", params={"about": message}, headers=self._headers)
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.error("Failed to update bio after attempts: %s", e)
            return False

    def album_name(self, album_id: str) -> str | None:
        """Return the name of an album with thread-safe cache.

        Args:
            album_id: Album ID.

        Returns:
            Album name or None on error.
        """
        with self._album_name_cache_lock:
            if album_id in self._album_name_cache:
                return self._album_name_cache[album_id]

        name = self._fetch_album_name(album_id)

        with self._album_name_cache_lock:
            self._album_name_cache[album_id] = name
        return name

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    def _fetch_album_name(self, album_id: str) -> str | None:
        """Fetch the album name from the API."""
        try:
            response = self.client.get(
                f"/{album_id}", params={"fields": "name"}, headers=self._headers
            )
            response.raise_for_status()
            return response.json().get("name")
        except httpx.HTTPError as e:
            logger.error("Failed to get album name %s after attempts: %s", album_id, e)
            return None

    def album_repost(
        self,
        message: str = "",
        frame_path: Path | None = None,
        album_id: str | None = None,
        reposting: bool = False,
    ) -> str | None:
        """Repost a frame directly to an album (published).

        Args:
            message: Optional message.
            frame_path: Path to the image.
            album_id: Album ID.
            reposting: If True, enables repost.

        Returns:
            Photo ID or None on error.
        """
        if not reposting or not album_id or not frame_path:
            return None

        if not str(album_id).isdigit():
            logger.error(
                "Album repost enabled but album_id %r is not a valid integer",
                album_id,
            )
            return None

        photo_id = self.upload_photo(frame_path, message=message, album_id=album_id, published=True)
        if not photo_id:
            logger.error("Failed to repost frame to album %s", album_id)
            return None

        return photo_id
