import os
from copy import deepcopy
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from pydantic import ValidationError

from src.config_models import AppConfig
from src.logger import get_logger
from src.settings import CONFIGS_PATH as DEFAULT_CONFIGS_PATH

# Creating YAML instance and configuring it for consistent YAML parsing and writing
yaml: YAML = YAML()
yaml.preserve_quotes = True  # Preserves quotes in YAML values
yaml.indent(
    mapping=2, sequence=4, offset=2
)  # Sets indentation for mappings and sequences
yaml.default_flow_style = False  # Uses block style for YAML
yaml.width = 4096  # Prevents line wrapping

logger = get_logger(__name__)


def _merge_yaml(base: CommentedMap | dict, updates: dict) -> CommentedMap | dict:
    """Recursively merge plain dict updates into an existing YAML mapping."""
    if isinstance(base, CommentedMap) and isinstance(updates, dict):
        result = deepcopy(base)
        for key, value in updates.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = _merge_yaml(result[key], value)
            else:
                result[key] = deepcopy(value)
        return result

    return deepcopy(updates)


def load_configs(config_path: Path | str | None = None) -> dict:
    """
    Loads configuration from the YAML file defined by config_path or the default config path.

    Returns:
        dict: The configuration data loaded from the YAML file, or an empty dict if loading fails.
    """
    if config_path is None:
        config_path = DEFAULT_CONFIGS_PATH
    config_path = Path(config_path)
    if not config_path.is_absolute():
        config_path = DEFAULT_CONFIGS_PATH.parent / config_path

    if not config_path.exists():
        logger.error("Config file not found at %s", config_path)
        return {}

    try:
        with config_path.open("r", encoding="utf-8") as file:
            configs = yaml.load(file)
            if configs is None:
                logger.warning(
                    "Config file %s is empty; returning empty dict", config_path.name
                )
                return {}
            return configs
    except (OSError, ValueError) as error:
        logger.error(
            "Failed to load %s: %s: %s",
            config_path.name,
            type(error).__name__,
            error,
            exc_info=True,
        )
        return {}


def load_and_validate(config_path: Path | str | None = None) -> AppConfig:
    """
    Load the YAML config file and validate it through Pydantic.

    Args:
        config_path: Optional path to the YAML configuration file.

    Returns:
        AppConfig: The validated configuration object.

    Raises:
        SystemExit: If the file is missing, empty, or fails validation.
    """
    raw = load_configs(config_path)
    if not raw:
        logger.critical("Cannot proceed without a valid configs.yml — exiting.")
        raise SystemExit(1)

    try:
        return AppConfig.model_validate(raw)
    except ValidationError as exc:
        logger.critical("configs.yml validation failed:\n%s", exc)
        raise SystemExit(1) from exc


def save_configs(configs: dict, config_path: Path | str | None = None) -> None:
    """
    Atomically writes the configuration dict back to the configured YAML path.

    It starts from the already-loaded YAML structure so existing comments and
    formatting are preserved instead of being replaced by a fresh plain-dict
    dump.
    """
    if config_path is None:
        config_path = DEFAULT_CONFIGS_PATH
    config_path = Path(config_path)
    if not config_path.is_absolute():
        config_path = DEFAULT_CONFIGS_PATH.parent / config_path

    tmp_path = config_path.with_suffix(config_path.suffix + ".tmp")
    try:
        original = load_configs(config_path)
        if not isinstance(original, CommentedMap):
            original = CommentedMap(original)

        updated = _merge_yaml(original, configs)

        with tmp_path.open("w", encoding="utf-8") as file:
            yaml.dump(updated, file)
        os.replace(tmp_path, config_path)
    except OSError as error:
        logger.error(
            "Failed to save %s: %s: %s",
            config_path.name,
            type(error).__name__,
            error,
            exc_info=True,
        )
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise
