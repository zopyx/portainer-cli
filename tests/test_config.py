from pathlib import Path

from portainer_cli.config import Config, get_config_path, load_config


def _mock_config_path(monkeypatch, tmp_path):
    cfg_path = tmp_path / "config.toml"
    monkeypatch.setattr("portainer_cli.config.get_config_path", lambda: cfg_path)
    monkeypatch.setattr("portainer_cli.config.CONFIG_FILE", cfg_path)
    return cfg_path


def test_config_defaults():
    cfg = Config()
    assert cfg.url == ""
    assert cfg.api_key == ""
    assert cfg.environment == ""


def test_get_config_path_xdg(monkeypatch, tmp_path):
    xdg = tmp_path / "xdg"
    xdg.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    path = get_config_path()
    assert path == xdg / "portainer-cli" / "config.toml"


def test_get_config_path_default(monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    path = get_config_path()
    assert path == Path.home() / ".portainer-cli" / "config.toml"


def test_load_config_empty_env(monkeypatch, tmp_path):
    _mock_config_path(monkeypatch, tmp_path)
    monkeypatch.delenv("PORTAINER_URL", raising=False)
    monkeypatch.delenv("PORTAINER_API_KEY", raising=False)
    monkeypatch.delenv("PORTAINER_ENVIRONMENT", raising=False)
    cfg = load_config()
    assert cfg.url == ""
    assert cfg.api_key == ""


def test_load_config_env_vars(monkeypatch):
    monkeypatch.setenv("PORTAINER_URL", "http://env-url.com")
    monkeypatch.setenv("PORTAINER_API_KEY", "env-key")
    monkeypatch.setenv("PORTAINER_ENVIRONMENT", "prod")
    cfg = load_config()
    assert cfg.url == "http://env-url.com"
    assert cfg.api_key == "env-key"
    assert cfg.environment == "prod"
