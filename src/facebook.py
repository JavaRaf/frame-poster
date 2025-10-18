import os
import re
from pathlib import Path
from typing import List

import httpx
from dotenv import load_dotenv
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.frame_utils import client, timestamp_to_frame
from src.load_configs import load_configs
from src.logger import get_logger

logger = get_logger(__name__)
FB_LOG_PATH = Path.cwd() / "logs" / "fb_log.txt"
FB_LOG_PATH.touch(exist_ok=True)

# Carrega as variáveis de ambiente do arquivo .env
# O parâmetro override=False garante que as variáveis de ambiente não sejam sobrescritas
#  se já estiverem definidas no ambiente do sistema operacional

CONFIGS = load_configs()
load_dotenv(".env") 

# Define a classe FacebookAPI para interagir com a API do Facebook
# A classe é inicializada com a versão da API e o token de acesso


class FacebookAPI:
    def __init__(self, api_version: str = "v21.0"):
        if not os.getenv("FB_TOKEN"):
            logger.error("FB_TOKEN not defined")
            raise ValueError("FB_TOKEN not defined")

        self.base_url = f"https://graph.facebook.com/{api_version}"
        self.access_token = os.getenv("FB_TOKEN", None)
        self.client = httpx.Client(base_url=self.base_url, timeout=httpx.Timeout(30, connect=10))


    @retry(
        stop=stop_after_attempt(3),  # Máximo de 3 tentativas
        wait=wait_exponential(
            multiplier=1, min=2, max=10
        ),  # Tempo de espera exponencial
        retry=retry_if_exception_type(
            httpx.HTTPError
        ),  # Só tenta novamente se for erro HTTP
        reraise=True,  # Lança exceção se todas as tentativas falharem
    )
    def _try_post(self, endpoint: str, params: dict, files: dict = None) -> str | None:
        response = self.client.post(endpoint, params=params, files=files)

        if response.status_code == 200:
            try:
                return response.json().get("id")
            except ValueError:
                logger.error('Error: Response does not contain valid JSON', exc_info=True)
                return None
        
        response.raise_for_status()  # Levanta exceção para ativar retry
        return None

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
        files = None


        if not frame_path:
            try:
                return self._try_post(endpoint, params)
            except RetryError:
                logger.error("Failed to post after multiple attempts", exc_info=True)
                return None
        
        with open(frame_path, "rb") as file:
            files = {"source": file}
            try:
                return self._try_post(endpoint, params, files)
            except RetryError:
                logger.error("Failed to post after multiple attempts", exc_info=True)
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
        except Exception as e:
            logger.error(f"Error while saving fb log: {e}", exc_info=True)



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
            return False
            
        except Exception as e:
            logger.error(f"Failed to update bio: {e}", exc_info=True)
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
            logger.error("reposting to album is enabled but album ID is not a valid integer", exc_info=True)
            return None

        endpoint = f"{self.base_url}/{album_id}/photos"
        params = {"access_token": self.access_token}
        files = {"source": frame_path}
        try:
            print(
            f"├── Reposting frame to album {album_id}...",
            flush=True,
            )
            return self.post_frame(message, frame_path, album_id)
        except RetryError:
            logger.error("Failed to repost frame to album after multiple attempts", exc_info=True)
            return None

        

    