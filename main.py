from src.load_configs import load_and_validate, save_configs
from src.config_validator import ValidationError


config = load_and_validate()

seasons = config.get("seasons", [])
season_name = seasons[0]["season"]
episode = seasons[0]["episodes"][0]
episode_name = episode["episode"]

print(season_name)
print(episode_name)
print(config.get("posting", {}).get("album_respost", False))

    
    


















