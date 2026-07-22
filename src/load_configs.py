from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from pathlib import Path

from src.config_validator import validate_config, ValidationError

yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(
    mapping=2,
    sequence=4,
    offset=2,
)

config_path = Path("config.yml")


def load_configs() -> CommentedMap:
    """
    Load configuration from a YAML file preserving comments and formatting.
    
    Returns:
        CommentedMap: The configuration data loaded from the YAML file with comments preserved
    """
    try:
        with open(config_path, "r", encoding="utf-8") as file:
            return yaml.load(file)
    except (Exception, OSError) as e:
        print(f"Error loading config file {config_path}: {e}")
        return {}


def load_and_validate() -> CommentedMap:
    """
    Load configuration and validate it using custom validator.
    
    Returns:
        CommentedMap: The validated configuration with comments preserved
        
    Raises:
        ValidationError: If the configuration fails validation
    """
    config = load_configs()
    if not config:
        raise ValidationError("Config file is empty or could not be loaded")
    
    validate_config(config)
    return config


def save_configs(config: CommentedMap) -> None:
    """
    Save configuration to a YAML file preserving comments and formatting.
    
    Args:
        config: The CommentedMap configuration data to save
    """
    try:
        with open(config_path, "w", encoding="utf-8") as file:
            yaml.dump(config, file)
    except (Exception, OSError) as e:
        print(f"Error saving config file {config_path}: {e}")


