"""Configuration loader with inheritance: global → workspace → project."""

import os
from pathlib import Path
from typing import Any

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
