"""System initialization — creates ~/.cipher-os structure on first run."""

from pathlib import Path

import yaml

from .config import DEFAULT_CONFIG, get_cipher_home


def init_cipher_os(name: str = "CIPHER-OS") -> Path:
    """Initialize CIPHER-OS directory structure. Idempotent."""
    home = get_cipher_home()

    # Core directories
    dirs = [
        home / "agents" / "cipher",
        home / "agents" / "lens",
        home / "agents" / "atlas",
        home / "agents" / "forge",
        home / "agents" / "sentinel",
        home / "rules",
        home / "knowledge",
        home / "workspaces",
        home / "skills",
        home / "scripts",
        home / "backups",
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Write global config if not exists
    config_path = home / "config.yaml"
    if not config_path.exists():
        config = DEFAULT_CONFIG.copy()
        config["name"] = name
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

    return home
