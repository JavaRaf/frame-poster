import os
from pathlib import Path

from ruamel.yaml import YAML

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



def save_configs(configs: dict) -> None:
    """
    Atomically writes the configuration dict back to ``configs.yml``.

    Writing to a sibling temp file and then renaming avoids leaving the
    config in a half-written state if the process is killed mid-write
    (a real risk in CI/CD where the job can be cancelled at any moment).
    """
    tmp_path = CONFIGS_PATH.with_suffix(CONFIGS_PATH.suffix + ".tmp")
    try:
        with tmp_path.open("w", encoding="utf-8") as file:
            yaml.dump(configs, file)
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