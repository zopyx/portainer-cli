# AGENTS.md — portainer-cli

## Project

A CLI tool for managing Portainer stacks and services. Built with Click and httpx.

## Architecture

```
src/portainer_cli/
  __init__.py    — empty
  __main__.py    — entry point (calls cli.main)
  cli.py         — Click CLI groups and commands
  client.py      — Portainer REST API client + log stream parser
  config.py      — TOML config loading with env var override
```

## Key files

| File         | Purpose                                    |
|--------------|--------------------------------------------|
| `cli.py`     | Click groups: `stack`, `service`, `config` |
| `client.py`  | `PortainerClient` + `LogStreamParser`      |
| `config.py`  | `Config` dataclass, `load_config()`        |

## Commands

- `portainer-cli stack list` — list stacks
- `portainer-cli stack pull-and-redeploy <name>` — redeploy from git or file
- `portainer-cli service status <name>` — service details and task counts
- `portainer-cli service logs <name>` — fetch/stream Docker logs
- `portainer-cli config init` — interactive config creation
- `portainer-cli config show` — display config (key masked)

## Dependencies

- `click>=8.0` — CLI framework
- `httpx>=0.24` — HTTP client

## Conventions

- No type stubs, no mypy, no tests currently
- Error handling via `PortainerError` exception, caught in CLI with `click.Abort()`
- Config: TOML file with env var override (env vars take precedence)
- Log streaming uses Docker's multiplexed log protocol (8-byte header + frame)
