"""Workspace manager — create, list, configure, validate workspaces."""

import shutil
from pathlib import Path
from typing import Optional

import yaml

from .config import get_cipher_home, load_yaml


WORKSPACE_DIRS = [
    "config.yaml",
    "memories",
    "knowledge",
    "sessions",
    "tickets",
    "projects",
    "skills",
]


def get_workspaces_root() -> Path:
    """Get the workspaces root directory."""
    return get_cipher_home() / "workspaces"


def list_workspaces() -> list[dict]:
    """List all workspaces with basic metadata."""
    root = get_workspaces_root()
    if not root.exists():
        return []

    workspaces = []
    for ws_dir in sorted(root.iterdir()):
        if ws_dir.is_dir():
            config = load_yaml(ws_dir / "config.yaml")
            projects = []
            proj_dir = ws_dir / "projects"
            if proj_dir.exists():
                projects = [p.name for p in proj_dir.iterdir() if p.is_dir()]

            workspaces.append({
                "name": ws_dir.name,
                "path": str(ws_dir),
                "projects": projects,
                "project_count": len(projects),
                "config": config,
            })

    return workspaces


def create_workspace(
    name: str,
    config: Optional[dict] = None,
) -> Path:
    """Create a new workspace with standard directory structure."""
    root = get_workspaces_root()
    ws_path = root / name

    if ws_path.exists():
        raise ValueError(f"Workspace '{name}' already exists")

    # Create directory structure
    ws_path.mkdir(parents=True)
    for d in WORKSPACE_DIRS:
        if d.endswith(".yaml"):
            # It's a file template
            (ws_path / d).touch()
        else:
            (ws_path / d).mkdir()

    # Write config
    ws_config = config or {
        "name": name,
        "routing": {"mode": "supervised"},
    }
    with open(ws_path / "config.yaml", "w") as f:
        yaml.dump(ws_config, f, default_flow_style=False)

    return ws_path


def delete_workspace(name: str, confirm: bool = False) -> bool:
    """Delete a workspace. Requires confirm=True as safety guard."""
    if not confirm:
        raise ValueError("Must pass confirm=True to delete a workspace")

    ws_path = get_workspaces_root() / name
    if not ws_path.exists():
        raise ValueError(f"Workspace '{name}' does not exist")

    shutil.rmtree(ws_path)
    return True


def get_workspace_path(name: str) -> Path:
    """Get path to a workspace, raise if doesn't exist."""
    ws_path = get_workspaces_root() / name
    if not ws_path.exists():
        raise ValueError(f"Workspace '{name}' does not exist")
    return ws_path


def create_project(workspace: str, project: str, config: Optional[dict] = None) -> Path:
    """Create a project within a workspace."""
    ws_path = get_workspace_path(workspace)
    proj_path = ws_path / "projects" / project

    if proj_path.exists():
        raise ValueError(f"Project '{project}' already exists in workspace '{workspace}'")

    proj_path.mkdir(parents=True)
    (proj_path / "repo").mkdir()

    # Write project config
    proj_config = config or {}
    if proj_config:
        with open(proj_path / ".cipher.yaml", "w") as f:
            yaml.dump(proj_config, f, default_flow_style=False)

    return proj_path


def get_allowed_paths(workspace: str, agent: str) -> list[str]:
    """Get allowed paths for an agent in a workspace (path-scoping enforcement)."""
    home = get_cipher_home()
    ws_path = get_workspaces_root() / workspace

    paths = [
        str(ws_path),                    # Own workspace (read+write)
        str(home / "knowledge"),         # Global KB (read-only)
    ]

    # Cipher gets broader access
    if agent == "cipher":
        paths.append(str(home / "workspaces"))  # All ticket boards
        paths.append(str(home / "activity.db"))

    return paths
