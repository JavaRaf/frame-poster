import os
from copy import deepcopy
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from pydantic import ValidationError

from src.config_models import AppConfig
from src.logger import get_logger

# Creating YAML instance and configuring it for consistent YAML parsing and writing
yaml: YAML = YAML()
yaml.preserve_quotes = True  # Preserves quotes in YAML values
yaml.indent(mapping=2, sequence=4, offset=2)  # Sets indentation for mappings and sequences
yaml.default_flow_style = False  # Uses block style for YAML
yaml.width = 4096  # Prevents line wrapping

logger = get_logger(__name__)

# Defining the path to the configuration file
CONFIGS_PATH = Path.cwd() / "configs.yml"


def _merge_yaml(base: CommentedMap | dict, updates: dict) -> CommentedMap | dict:
    """Recursively merge plain dict updates into an existing YAML mapping."""
    if isinstance(base, CommentedMap) and isinstance(updates, dict):
        result = deepcopy(base)
        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = _merge_yaml(result[key], value)
            else:
                result[key] = deepcopy(value)
        return result

    return deepcopy(updates)


def load_configs() -> dict:
    """
    Loads configuration from the YAML file defined in CONFIGS_PATH.

    Returns:
        dict: The configuration data loaded from the YAML file, or an empty dict if loading fails.
    """
    if not CONFIGS_PATH.exists():
        # Missing file is not a caught exception, so no exc_info here.
        logger.error("Config file not found at %s", CONFIGS_PATH)
        return {}

    try:
        with CONFIGS_PATH.open("r", encoding="utf-8") as file:
            configs = yaml.load(file)
            if configs is None:
                logger.warning("Config file %s is empty; returning empty dict", CONFIGS_PATH.name)
                return {}
            return configs
    except (OSError, ValueError) as error:
        logger.error("Failed to load %s: %s: %s", CONFIGS_PATH.name, type(error).__name__, error, exc_info=True)
        return {}


def load_and_validate() -> AppConfig:
    """
    Load ``configs.yml`` and validate it through Pydantic.

    Returns:
        AppConfig: The validated configuration object.

    Raises:
        SystemExit: If the file is missing, empty, or fails validation.
    """
    raw = load_configs()
    if not raw:
        logger.critical("Cannot proceed without a valid configs.yml — exiting.")
        raise SystemExit(1)

    try:
        return AppConfig.model_validate(raw)
    except ValidationError as exc:
        logger.critical("configs.yml validation failed:\n%s", exc)
        raise SystemExit(1) from exc



def save_configs(configs: dict) -> None:
    """
    Atomically writes the configuration dict back to ``configs.yml``.

    It starts from the already-loaded YAML structure so existing comments and
    formatting are preserved instead of being replaced by a fresh plain-dict
    dump.
    """
    tmp_path = CONFIGS_PATH.with_suffix(CONFIGS_PATH.suffix + ".tmp")
    try:
        original = load_configs()
        if not isinstance(original, CommentedMap):
            original = CommentedMap(original)

        updated = _merge_yaml(original, configs)

        with tmp_path.open("w", encoding="utf-8") as file:
            yaml.dump(updated, file)
        # ``os.replace`` is atomic on both POSIX and Windows when source and
        # destination live on the same filesystem, which is the case here.
        os.replace(tmp_path, CONFIGS_PATH)
    except OSError as error:
        logger.error("Failed to save %s: %s: %s", CONFIGS_PATH.name, type(error).__name__, error, exc_info=True)
        # Best-effort cleanup of the partial file so it doesn't linger.
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise