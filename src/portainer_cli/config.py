import os
from dataclasses import dataclass
from pathlib import Path

import tomllib

CONFIG_DIR = Path.home() / ".portainer-cli"
CONFIG_FILE = CONFIG_DIR / "config.toml"


@dataclass
class Config:
    url: str = ""
    api_key: str = ""
    environment: str = ""


def get_config_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "portainer-cli" / "config.toml"
    return CONFIG_FILE


def load_config() -> Config:
    cfg = Config()
    path = get_config_path()
    if path.exists():
        with open(path, "rb") as f:
            data = tomllib.load(f)
        cfg.url = data.get("url", "")
        cfg.api_key = data.get("api_key", "")
        cfg.environment = data.get("environment", "")

    cfg.url = os.environ.get("PORTAINER_URL", cfg.url)
    cfg.api_key = os.environ.get("PORTAINER_API_KEY", cfg.api_key)
    cfg.environment = os.environ.get("PORTAINER_ENVIRONMENT", cfg.environment)
    return cfg
