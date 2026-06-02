"""Settings routes — config management."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

import yaml

from ...core.config import get_cipher_home, load_config

router = APIRouter()


class ConfigUpdate(BaseModel):
    config: dict


class PricingUpdate(BaseModel):
    models: dict


@router.get("")
async def get_settings():
    """Get current global configuration."""
    return load_config()


@router.put("")
async def update_settings(body: ConfigUpdate):
    """Update global configuration (partial merge)."""
    home = get_cipher_home()
    config_path = home / "config.yaml"

    # Load existing
    existing = {}
    if config_path.exists():
        with open(config_path) as f:
            existing = yaml.safe_load(f) or {}

    # Merge
    from ...core.config import deep_merge
    updated = deep_merge(existing, body.config)

    with open(config_path, "w") as f:
        yaml.dump(updated, f, default_flow_style=False)

    return {"success": True, "config": updated}


@router.get("/pricing")
async def get_pricing():
    """Get model pricing table."""
    config = load_config()
    return {"models": config.get("pricing", {})}


@router.put("/pricing")
async def update_pricing(body: PricingUpdate):
    """Update model pricing table."""
    home = get_cipher_home()
    config_path = home / "config.yaml"

    existing = {}
    if config_path.exists():
        with open(config_path) as f:
            existing = yaml.safe_load(f) or {}

    existing["pricing"] = body.models

    with open(config_path, "w") as f:
        yaml.dump(existing, f, default_flow_style=False)

    return {"success": True}
