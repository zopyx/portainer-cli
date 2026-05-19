from click.testing import CliRunner

from portainer_cli.cli import cli


def test_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output


def test_stack_list_no_config(monkeypatch, tmp_path):
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text("")
    monkeypatch.setattr("portainer_cli.config.get_config_path", lambda: cfg_path)
    monkeypatch.setattr("portainer_cli.config.CONFIG_FILE", cfg_path)
    monkeypatch.delenv("PORTAINER_URL", raising=False)
    monkeypatch.delenv("PORTAINER_API_KEY", raising=False)
    runner = CliRunner()
    result = runner.invoke(cli, ["stack", "list"])
    assert result.exit_code != 0
    assert "not configured" in result.output


def test_config_show():
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "show"])
    assert result.exit_code == 0
    assert "Config file:" in result.output


def test_unknown_command():
    runner = CliRunner()
    result = runner.invoke(cli, ["bogus"])
    assert result.exit_code != 0
    assert "No such command" in result.output
