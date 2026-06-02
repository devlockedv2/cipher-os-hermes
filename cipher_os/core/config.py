"""Configuration loader with inheritance: global → workspace → project."""

import os
from pathlib import Path
from typing import Any, Optional

import yaml


DEFAULT_CONFIG = {
    "version": "0.1.0",
    "name": "CIPHER-OS",
    "server": {
        "host": "127.0.0.1",
        "port": 9800,
        "cors_origins": ["http://localhost:3000"],
    },
    "routing": {
        "mode": "supervised",  # supervised | autonomous
    },
    "escalation": {
        "cost_threshold": 5.00,
    },
    "communication": {
        "direct_queries": True,
        "direct_query_timeout": 60,
        "max_direct_per_task": 3,
    },
    "recovery": {
        "heartbeat_interval": 30,
        "heartbeat_timeout": 90,
        "max_attempts": 3,
        "checkpoint_on_interrupt": True,
        "time_limits": {
            "sm": 15,
            "md": 60,
            "lg": 180,
            "xl": 480,
        },
    },
    "watchdog": {
        "enabled": True,
        "cipher_max_restarts": 3,
        "cipher_restart_window": 300,
        "alert_channels": ["telegram"],
    },
    "pricing": {
        "claude-opus-4": {"input": 15.0, "output": 75.0},
        "claude-sonnet-4": {"input": 3.0, "output": 15.0},
    },
    "agents": {
        "cipher": {"model": None},  # None = inherit default
        "lens": {"model": None},
        "atlas": {"model": None},
        "forge": {"model": None},
        "sentinel": {"model": None},
    },
}


def get_cipher_home() -> Path:
    """Get CIPHER-OS home directory."""
    return Path(os.environ.get("CIPHER_HOME", Path.home() / ".cipher-os"))


def load_yaml(path: Path) -> dict:
    """Load a YAML file, return empty dict if missing."""
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override into base. Override wins on conflicts."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(
    workspace: str | None = None,
    project: str | None = None,
) -> dict[str, Any]:
    """Load config with inheritance chain: default → global → workspace → project."""
    home = get_cipher_home()

    # Start with defaults
    config = DEFAULT_CONFIG.copy()

    # Layer 1: Global config
    global_config = load_yaml(home / "config.yaml")
    config = deep_merge(config, global_config)

    # Layer 2: Workspace config
    if workspace:
        ws_config = load_yaml(home / "workspaces" / workspace / "config.yaml")
        config = deep_merge(config, ws_config)

    # Layer 3: Project config
    if workspace and project:
        proj_config = load_yaml(
            home / "workspaces" / workspace / "projects" / project / ".cipher.yaml"
        )
        config = deep_merge(config, proj_config)

    return config


def save_config(config: dict, workspace: Optional[str] = None) -> None:
    """Persist config back to disk (global or workspace config.yaml)."""
    home = get_cipher_home()
    if workspace:
        path = home / "workspaces" / workspace / "config.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
    else:
        path = home / "config.yaml"
    with open(path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def get_linear_api_key(workspace: str) -> Optional[str]:
    """Return the Linear API key for a workspace, or None if not configured."""
    home = get_cipher_home()
    ws_config = load_yaml(home / "workspaces" / workspace / "config.yaml")
    return ws_config.get("integrations", {}).get("linear", {}).get("api_key") or None


def set_linear_api_key(workspace: str, api_key: str) -> None:
    """Store the Linear API key for a workspace."""
    home = get_cipher_home()
    path = home / "workspaces" / workspace / "config.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    cfg = load_yaml(path)
    cfg.setdefault("integrations", {}).setdefault("linear", {})["api_key"] = api_key
    with open(path, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)

