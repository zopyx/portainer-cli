import sys
import click

from .config import load_config, get_config_path, Config, CONFIG_DIR
from .client import PortainerClient, PortainerError


def _get_client(ctx) -> PortainerClient:
    return ctx.obj["client"]


def _require_config(ctx):
    cfg: Config = ctx.obj["config"]
    if not cfg.url:
        click.echo(
            "Error: Portainer URL not configured.\n"
            "  Set PORTAINER_URL env var or run: portainer-cli config init",
            err=True,
        )
        raise click.Abort()
    if not cfg.api_key:
        click.echo(
            "Error: Portainer API key not configured.\n"
            "  Set PORTAINER_API_KEY env var or run: portainer-cli config init",
            err=True,
        )
        raise click.Abort()
    return cfg


@click.group()
@click.option("--url", envvar="PORTAINER_URL", default="", help="Portainer URL")
@click.option(
    "--api-key", envvar="PORTAINER_API_KEY", default="", help="Portainer API key"
)
@click.pass_context
def cli(ctx, url, api_key):
    ctx.ensure_object(dict)
    cfg = load_config()
    if url:
        cfg.url = url
    if api_key:
        cfg.api_key = api_key
    ctx.obj["config"] = cfg
    if cfg.url and cfg.api_key:
        ctx.obj["client"] = PortainerClient(cfg.url, cfg.api_key)
    else:
        ctx.obj["client"] = None


@cli.group()
def stack():
    """Manage Portainer stacks"""


@stack.command()
@click.pass_context
def list(ctx):
    """List all stacks"""
    cfg = _require_config(ctx)
    client = _get_client(ctx)
    try:
        stacks = client.get_stacks()
        if not stacks:
            click.echo("No stacks found.")
            return
        click.echo(client.format_stack_list(stacks))
    except PortainerError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort() from e


@stack.command(name="pull-and-redeploy")
@click.argument("name")
@click.option(
    "--repull/--no-repull",
    default=True,
    help="Repull images and redeploy (default: repull)",
)
@click.pass_context
def pull_and_redeploy(ctx, name, repull):
    """Pull latest images and redeploy a stack by NAME"""
    _require_config(ctx)
    client = _get_client(ctx)
    try:
        msg = client.redeploy_stack(name, repull=repull)
        click.echo(msg)
    except PortainerError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort() from e


@cli.group()
def service():
    """Manage Docker services"""


@service.command()
@click.argument("name")
@click.option("--env", "env_name", help="Environment name (default from config)")
@click.pass_context
def status(ctx, name, env_name):
    """Show service status by NAME"""
    cfg = _require_config(ctx)
    client = _get_client(ctx)
    env = env_name or cfg.environment
    if not env:
        click.echo(
            "Error: No environment specified. Set PORTAINER_ENVIRONMENT or pass --env",
            err=True,
        )
        raise click.Abort()

    try:
        ep = client.get_endpoint_by_name(env)
        svc = client.get_service_by_name(ep["Id"], name)
        click.echo(client.format_service_status(svc))
    except PortainerError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort() from e


@service.command()
@click.argument("name")
@click.option("--env", "env_name", help="Environment name (default from config)")
@click.option(
    "--tail",
    default=100,
    type=int,
    help="Number of recent log lines (default: 100)",
)
@click.option(
    "--follow", "-f", is_flag=True, help="Follow log output (tail -f style)"
)
@click.pass_context
def logs(ctx, name, env_name, tail, follow):
    """Fetch or stream logs for a service by NAME"""
    cfg = _require_config(ctx)
    client = _get_client(ctx)
    env = env_name or cfg.environment
    if not env:
        click.echo(
            "Error: No environment specified. Set PORTAINER_ENVIRONMENT or pass --env",
            err=True,
        )
        raise click.Abort()

    try:
        ep = client.get_endpoint_by_name(env)
        svc = client.get_service_by_name(ep["Id"], name)
        sid = svc["ID"]
        eid = ep["Id"]
    except PortainerError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort() from e

    try:
        if follow:
            for stype, line in client.stream_logs(eid, sid, tail=tail):
                _write_log_line(stype, line)
        else:
            lines = client.fetch_logs(eid, sid, tail=tail)
            for stype, line in lines:
                _write_log_line(stype, line)
    except PortainerError as e:
        click.echo(f"\nError: {e}", err=True)
        raise click.Abort() from e


def _write_log_line(stream_type: int, line: str):
    sys.stdout.write(line)
    if not line.endswith("\n"):
        sys.stdout.write("\n")
    sys.stdout.flush()


@cli.group()
def config():
    """Manage portainer-cli configuration"""


@config.command()
@click.option("--force", is_flag=True, help="Overwrite existing config")
def init(force):
    """Create configuration interactively"""
    path = get_config_path()
    if path.exists() and not force:
        click.confirm(
            f"Config exists at {path}. Overwrite?", abort=True, err=True
        )

    click.echo("Portainer CLI Configuration")
    click.echo("---")
    url = click.prompt("Portainer URL", type=str)
    api_key = click.prompt("API Key", type=str, hide_input=True)
    env = click.prompt(
        "Default environment name", type=str, default="primary"
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'url = "{url}"\napi_key = "{api_key}"\nenvironment = "{env}"\n'
    )
    path.chmod(0o600)
    click.echo(f"Config written to {path}")


@config.command()
def show():
    """Show current configuration"""
    cfg = load_config()
    path = get_config_path()
    click.echo(f"Config file: {path}")
    click.echo(f"URL:         {cfg.url or '(not set)'}")
    click.echo(f"API key:     {'***' if cfg.api_key else '(not set)'}")
    click.echo(f"Environment: {cfg.environment or '(not set)'}")


def main():
    cli()


if __name__ == "__main__":
    main()
