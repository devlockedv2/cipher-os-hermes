"""Agents routes — monitor and manage agents."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ...agents import AGENT_NAMES, AGENT_ROLES, get_agent_personality, build_system_prompt
from ...core.config import get_cipher_home

router = APIRouter()


class PersonalityUpdate(BaseModel):
    content: str


@router.get("")
async def list_agents():
    """List all agents with their status."""
    agents = []
    for name in AGENT_NAMES:
        agents.append({
            "name": name,
            "role": AGENT_ROLES[name],
            "status": "idle",
            "current_task": None,
            "workspace": None,
        })
    return agents


@router.get("/{agent_name}")
async def get_agent(agent_name: str):
    """Get detailed info about an agent."""
    if agent_name not in AGENT_NAMES:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    personality = get_agent_personality(agent_name)
    home = get_cipher_home()
    has_local = (home / "agents" / agent_name / "personality.local.md").exists()

    return {
        "name": agent_name,
        "role": AGENT_ROLES[agent_name],
        "status": "idle",
        "current_task": None,
        "personality_md": personality,
        "has_local_override": has_local,
    }


@router.put("/{agent_name}/personality")
async def update_personality(agent_name: str, body: PersonalityUpdate):
    """Update agent personality (writes personality.local.md)."""
    if agent_name not in AGENT_NAMES:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    home = get_cipher_home()
    local_path = home / "agents" / agent_name / "personality.local.md"
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(body.content)

    return {"success": True, "message": f"Personality updated for {agent_name}"}


@router.delete("/{agent_name}/personality")
async def reset_personality(agent_name: str):
    """Reset agent personality to default (deletes local override)."""
    if agent_name not in AGENT_NAMES:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    home = get_cipher_home()
    local_path = home / "agents" / agent_name / "personality.local.md"
    if local_path.exists():
        local_path.unlink()

    return {"success": True, "message": f"Personality reset to default for {agent_name}"}
