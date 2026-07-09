import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent

CONFIG_FILE_ENV = os.getenv("CONFIG_FILE")
CONFIGS_PATH = Path(CONFIG_FILE_ENV) if CONFIG_FILE_ENV else ROOT_DIR / "configs.yml"
if not CONFIGS_PATH.is_absolute():
    CONFIGS_PATH = ROOT_DIR / CONFIGS_PATH

DOTENV_PATH = Path(os.getenv("DOTENV_PATH", ROOT_DIR / ".env"))
if not DOTENV_PATH.is_absolute():
    DOTENV_PATH = ROOT_DIR / DOTENV_PATH

load_dotenv(DOTENV_PATH, override=False)

LOG_DIR = Path(os.getenv("LOG_DIR", ROOT_DIR / "logs"))
FB_LOG_PATH = Path(os.getenv("FB_LOG_PATH", LOG_DIR / "facebook.log"))
IMAGES_DIR = Path(os.getenv("IMAGES_DIR", ROOT_DIR / "images"))
TEMP_DIR = Path(os.getenv("TEMP_DIR", ROOT_DIR / "temp"))
SUBTITLES_DIR = Path(os.getenv("SUBTITLES_DIR", ROOT_DIR / "subtitles"))

LOG_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)
SUBTITLES_DIR.mkdir(parents=True, exist_ok=True)

FB_TOKEN_ENV_VAR = "FB_TOKEN"

