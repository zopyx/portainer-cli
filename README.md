# portainer-cli

Minimal CLI for Portainer container management.

## Installation

```bash
uv pip install -e .
```

## Configuration

Config is stored at `~/.portainer-cli/config.toml` (or `$XDG_CONFIG_HOME/portainer-cli/config.toml`).

### Interactive

```bash
portainer-cli config init
```

### Environment variables

| Variable               | Description        |
|------------------------|--------------------|
| `PORTAINER_URL`        | Portainer URL      |
| `PORTAINER_API_KEY`    | API key            |
| `PORTAINER_ENVIRONMENT`| Default environment |

## Usage

```bash
portainer-cli stack list
portainer-cli stack pull-and-redeploy <name>
portainer-cli service status <name>
portainer-cli service logs <name>
portainer-cli service logs --follow <name>
portainer-cli config show
```

## Commands

- `stack list` – List all stacks
- `stack pull-and-redeploy <name>` – Pull images and redeploy a stack
- `service status <name>` – Show service details
- `service logs <name>` – Fetch or stream service logs
- `config init` – Create config interactively
- `config show` – Display current config
