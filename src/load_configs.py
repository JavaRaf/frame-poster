from pathlib import Path

from ruamel.yaml import YAML

from src.logger import get_logger

# Creating YAML instance and configuring it for consistent YAML parsing and writing
yaml: YAML = YAML()
yaml.preserve_quotes = True  # Preserves quotes in YAML values
yaml.indent(mapping=2, sequence=4, offset=2)  # Sets indentation for mappings and sequences
yaml.default_flow_style = False  # Uses block style for YAML

logger = get_logger(__name__)

# Defining the path to the configuration file
CONFIGS_PATH = Path.cwd() / "configs.yml"


def load_configs() -> dict:
    """
    Loads configuration from the YAML file defined in CONFIGS_PATH.

    Returns:
        dict: The configuration data loaded from the YAML file, or an empty dict if loading fails.
    """
    # Checks if the configuration file exists before attempting to load
    if not CONFIGS_PATH.exists():
        logger.error(f"Config file not found: {CONFIGS_PATH}", exc_info=True)
        return {}

    try:
        # Opens and loads the YAML configuration file
        with CONFIGS_PATH.open("r") as file:
            configs = yaml.load(file)
            # Ensures that a dictionary is always returned
            if configs is None:
                logger.warning("Config file is empty. Returning empty dict.")
                return {}
            return configs
    except Exception as error:
        # Logs any exception that occurs during loading
        logger.error(f"Error while loading configs: {error}", exc_info=True)
        return {}