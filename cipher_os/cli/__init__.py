"""CIPHER-OS CLI — main entry point."""

import click

from ..core.config import load_config
from ..core.init_system import init_cipher_os
from ..core.workspace import create_workspace, list_workspaces


@click.group()
@click.version_option(package_name="cipher-os")
def cli():
    """CIPHER-OS — Multi-agent OS layer for Hermes Agent."""
    pass


@cli.command()
@click.option("--name", default="CIPHER-OS", help="System name (for branding)")
def init(name: str):
    """Initialize CIPHER-OS directory structure."""
    home = init_cipher_os(name=name)
    click.echo(f"✓ Initialized {name} at {home}")


@cli.group()
def workspace():
    """Manage workspaces."""
    pass


@workspace.command("list")
def workspace_list():
    """List all workspaces."""
    workspaces = list_workspaces()
    if not workspaces:
        click.echo("No workspaces found. Create one with: cipher-os workspace create <name>")
        return

    for ws in workspaces:
        projects = ws["project_count"]
        click.echo(f"  {ws['name']} ({projects} project{'s' if projects != 1 else ''})")


@workspace.command("create")
@click.argument("name")
def workspace_create(name: str):
    """Create a new workspace."""
    try:
        path = create_workspace(name)
        click.echo(f"✓ Created workspace '{name}' at {path}")
    except ValueError as e:
        click.echo(f"✗ {e}", err=True)
        raise SystemExit(1)


@cli.command()
def status():
    """Show system status."""
    config = load_config()
    name = config.get("name", "CIPHER-OS")
    version = config.get("version", "unknown")
    workspaces = list_workspaces()

    click.echo(f"{name} v{version}")
    click.echo(f"Workspaces: {len(workspaces)}")
    for ws in workspaces:
        click.echo(f"  • {ws['name']}")


if __name__ == "__main__":
    cli()
