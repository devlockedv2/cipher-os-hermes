"""CIPHER-OS CLI — main entry point."""

import os
import sys
import time
import subprocess
import shutil
from pathlib import Path

import click

from ..core.config import load_config, get_cipher_home
from ..core.init_system import init_cipher_os
from ..core.workspace import create_workspace, list_workspaces


@click.group()
@click.version_option(package_name="cipher-os")
def cli():
    """CIPHER-OS — Multi-agent OS layer for Hermes Agent."""
    pass


@cli.command()
@click.option("--name", default="CIPHER-OS", help="System name (for branding)")
@click.option("--port", default=9800, help="Web UI port")
@click.option("--no-start", is_flag=True, help="Don't start the server after init")
def init(name: str, port: int, no_start: bool):
    """Initialize CIPHER-OS and start the server."""
    click.echo(f"\n  Initialising {name}...")
    home = init_cipher_os(name=name)
    click.echo(f"  ✓ Data directory ready at {home}")

    # Update port in config if custom
    if port != 9800:
        config_path = home / "config.yaml"
        import yaml
        with open(config_path) as f:
            config = yaml.safe_load(f)
        config.setdefault("server", {})["port"] = port
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        click.echo(f"  ✓ Port set to {port}")

    if not no_start:
        click.echo(f"\n  Starting server on port {port}...")
        _start_server(port)


@cli.command()
def update():
    """Update CIPHER-OS to the latest version."""
    install_dir = Path(__file__).parent.parent.parent
    click.echo("\n  Checking for updates...")

    # Fetch latest
    result = subprocess.run(
        ["git", "fetch", "origin", "main"],
        cwd=install_dir, capture_output=True, text=True
    )
    if result.returncode != 0:
        click.echo(f"  ✗ Failed to fetch: {result.stderr}", err=True)
        raise SystemExit(1)

    # Check if behind
    result = subprocess.run(
        ["git", "rev-list", "HEAD..origin/main", "--count"],
        cwd=install_dir, capture_output=True, text=True
    )
    behind = int(result.stdout.strip() or "0")

    if behind == 0:
        click.echo("  ✓ Already up to date")
        return

    click.echo(f"  {behind} new commit(s) available")

    # Pull
    click.echo("  Pulling latest...")
    result = subprocess.run(
        ["git", "pull", "--ff-only", "origin", "main"],
        cwd=install_dir, capture_output=True, text=True
    )
    if result.returncode != 0:
        click.echo(f"  ✗ Pull failed: {result.stderr}", err=True)
        raise SystemExit(1)
    click.echo("  ✓ Code updated")

    # Reinstall Python deps
    click.echo("  Updating dependencies...")
    venv_pip = install_dir / ".venv" / "bin" / "pip"
    uv = shutil.which("uv")
    if uv:
        subprocess.run(
            [uv, "pip", "install", "-e", ".[all]", "--python",
             str(install_dir / ".venv" / "bin" / "python")],
            cwd=install_dir, capture_output=True
        )
    elif venv_pip.exists():
        subprocess.run(
            [str(venv_pip), "install", "-e", ".[all]", "-q"],
            cwd=install_dir, capture_output=True
        )
    click.echo("  ✓ Dependencies updated")

    # Rebuild frontend if node available
    web_dir = install_dir / "web"
    if web_dir.exists() and shutil.which("npm"):
        click.echo("  Rebuilding frontend...")
        subprocess.run(
            ["npm", "install", "--silent"],
            cwd=web_dir, capture_output=True
        )
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=web_dir, capture_output=True, text=True
        )
        if result.returncode == 0:
            click.echo("  ✓ Frontend rebuilt")
        else:
            click.echo("  ! Frontend build failed — run manually: cd web && npm run build")

    # Restart service if running
    _restart_if_running()

    click.echo("\n  ✓ CIPHER-OS updated successfully\n")


@cli.command()
@click.option("--port", default=None, type=int, help="Port override")
def start(port: int):
    """Start the CIPHER-OS server."""
    config = load_config()
    p = port or config.get("server", {}).get("port", 9800)
    _start_server(p)


@cli.command()
def stop():
    """Stop the CIPHER-OS server."""
    home = get_cipher_home()
    pid_file = home / "server.pid"

    # Try systemd first
    result = subprocess.run(
        ["systemctl", "--user", "stop", "cipher-os"],
        capture_output=True
    )
    if result.returncode == 0:
        click.echo("  ✓ Service stopped")
        return

    # Fall back to PID file
    if pid_file.exists():
        pid = int(pid_file.read_text().strip())
        try:
            os.kill(pid, 15)
            pid_file.unlink()
            click.echo(f"  ✓ Server stopped (PID {pid})")
        except ProcessLookupError:
            click.echo("  ! Server was not running")
            pid_file.unlink()
    else:
        click.echo("  ! No server PID found — may not be running")


@cli.command()
def logs():
    """Tail the server logs."""
    home = get_cipher_home()
    log_file = home / "logs" / "server.log"

    if not log_file.exists():
        # Try journalctl
        os.execvp("journalctl", ["journalctl", "--user", "-u", "cipher-os", "-f", "--no-pager"])
    else:
        os.execvp("tail", ["tail", "-f", str(log_file)])


@cli.group()
def workspace():
    """Manage workspaces."""
    pass


@workspace.command("list")
def workspace_list():
    """List all workspaces."""
    workspaces = list_workspaces()
    if not workspaces:
        click.echo("  No workspaces found. Create one with: cipher-os workspace create <name>")
        return
    for ws in workspaces:
        projects = ws["project_count"]
        click.echo(f"  {ws['name']}  ({projects} project{'s' if projects != 1 else ''})")


@workspace.command("create")
@click.argument("name")
def workspace_create(name: str):
    """Create a new workspace."""
    try:
        path = create_workspace(name)
        click.echo(f"  ✓ Created workspace '{name}' at {path}")
    except ValueError as e:
        click.echo(f"  ✗ {e}", err=True)
        raise SystemExit(1)


@cli.command()
def status():
    """Show system status."""
    config = load_config()
    name = config.get("name", "CIPHER-OS")
    version = config.get("version", "unknown")
    port = config.get("server", {}).get("port", 9800)
    workspaces = list_workspaces()

    # Check if server is running
    try:
        import urllib.request
        urllib.request.urlopen(f"http://localhost:{port}/api/v1/health", timeout=2)
        server_status = "running"
    except Exception:
        server_status = "stopped"

    click.echo(f"\n  {name}  v{version}")
    click.echo(f"  Server:     {server_status} (port {port})")
    click.echo(f"  Workspaces: {len(workspaces)}")
    for ws in workspaces:
        click.echo(f"    • {ws['name']}")
    click.echo(f"  Data dir:   {get_cipher_home()}")
    click.echo("")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _start_server(port: int):
    """Start uvicorn server in background."""
    home = get_cipher_home()
    install_dir = Path(__file__).parent.parent.parent
    uvicorn = install_dir / ".venv" / "bin" / "uvicorn"

    if not uvicorn.exists():
        uvicorn_path = shutil.which("uvicorn")
        if not uvicorn_path:
            click.echo("  ✗ uvicorn not found in virtualenv", err=True)
            raise SystemExit(1)
        uvicorn = Path(uvicorn_path)

    log_dir = home / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    pid_file = home / "server.pid"
    log_file = log_dir / "server.log"

    env = os.environ.copy()
    env["CIPHER_HOME"] = str(home)

    with open(log_file, "a") as log:
        proc = subprocess.Popen(
            [str(uvicorn), "cipher_os.api:app",
             "--host", "0.0.0.0", "--port", str(port)],
            cwd=install_dir,
            env=env,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )
        pid_file.write_text(str(proc.pid))

    # Wait for health check
    for i in range(10):
        time.sleep(1)
        try:
            import urllib.request
            urllib.request.urlopen(f"http://localhost:{port}/api/v1/health", timeout=2)
            click.echo(f"  ✓ Server running at http://localhost:{port}")
            return
        except Exception:
            pass

    click.echo(f"  ! Server not responding after 10s — check logs at {log_file}")


def _restart_if_running():
    """Restart service if it's currently running."""
    result = subprocess.run(
        ["systemctl", "--user", "is-active", "cipher-os"],
        capture_output=True, text=True
    )
    if result.stdout.strip() == "active":
        click.echo("  Restarting service...")
        subprocess.run(["systemctl", "--user", "restart", "cipher-os"])
        click.echo("  ✓ Service restarted")


if __name__ == "__main__":
    cli()
