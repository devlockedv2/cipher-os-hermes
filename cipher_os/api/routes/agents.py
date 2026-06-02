"""Agents routes — monitor, configure, and manage agents."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ...agents import AGENT_NAMES, AGENT_ROLES, AGENT_COLORS, get_agent_personality, get_agent_status
from ...core.config import get_cipher_home, load_config, save_config
from ...activity.log import query as query_activity, stats as activity_stats

router = APIRouter()

AGENT_DESCRIPTIONS = {
    "cipher":   "Routes tasks, manages delegation, approves actions",
    "lens":     "Deep research, analysis, comparisons, evaluations",
    "atlas":    "Architecture, planning, estimation, scoping",
    "forge":    "Implementation, testing, debugging, deployment",
    "sentinel": "Infrastructure, security, monitoring, CI/CD",
}


class PersonalityUpdate(BaseModel):
    content: str


class AgentConfigUpdate(BaseModel):
    model: Optional[str] = None
    max_cost: Optional[float] = None
    routing_weight: Optional[float] = None
    enabled: Optional[bool] = None
    timeout: Optional[int] = None


@router.get("")
async def list_agents():
    """List all agents with status + config."""
    statuses = {a["name"]: a for a in get_agent_status()}
    config = load_config()
    home = get_cipher_home()
    agents_config = config.get("agents", {})

    result = []
    for name in AGENT_NAMES:
        s = statuses.get(name, {})
        ac = agents_config.get(name, {})
        has_local = (home / "agents" / name / "personality.local.md").exists()
        result.append({
            "name": name,
            "role": AGENT_ROLES[name],
            "color": AGENT_COLORS[name],
            "description": AGENT_DESCRIPTIONS[name],
            "status": s.get("status", "idle"),
            "tasks_completed": s.get("tasks_completed", 0),
            "tasks_failed":    s.get("tasks_failed", 0),
            "tasks_total":     s.get("tasks_total", 0),
            "total_cost":      s.get("total_cost", 0.0),
            "input_tokens":    s.get("input_tokens", 0),
            "output_tokens":   s.get("output_tokens", 0),
            "model": ac.get("model") or config.get("hermes", {}).get("model", "default"),
            "max_cost": ac.get("max_cost", 5.0),
            "routing_weight": ac.get("routing_weight", 1.0),
            "enabled": ac.get("enabled", True),
            "timeout": ac.get("timeout", 300),
            "has_local_prompt": has_local,
        })
    return result


@router.get("/{agent_name}")
async def get_agent(agent_name: str):
    """Get detailed info + personality for one agent."""
    if agent_name not in AGENT_NAMES:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    config = load_config()
    home = get_cipher_home()
    ac = config.get("agents", {}).get(agent_name, {})

    local_path = home / "agents" / agent_name / "personality.local.md"
    default_path = home / "agents" / agent_name / "personality.md"
    has_local = local_path.exists()

    # Return the active personality (local overrides default)
    personality = ""
    if has_local:
        personality = local_path.read_text()
    elif default_path.exists():
        personality = default_path.read_text()
    else:
        personality = get_agent_personality(agent_name)

    return {
        "name": agent_name,
        "role": AGENT_ROLES[agent_name],
        "description": AGENT_DESCRIPTIONS[agent_name],
        "status": "idle",
        "personality_md": personality,
        "has_local_prompt": has_local,
        "model": ac.get("model") or config.get("hermes", {}).get("model", "default"),
        "max_cost": ac.get("max_cost", 5.0),
        "routing_weight": ac.get("routing_weight", 1.0),
        "enabled": ac.get("enabled", True),
        "timeout": ac.get("timeout", 300),
    }


@router.put("/{agent_name}/config")
async def update_agent_config(agent_name: str, body: AgentConfigUpdate):
    """Update agent config (model, max_cost, routing_weight, enabled, timeout)."""
    if agent_name not in AGENT_NAMES:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    config = load_config()
    if "agents" not in config:
        config["agents"] = {}
    if agent_name not in config["agents"]:
        config["agents"][agent_name] = {}

    ac = config["agents"][agent_name]
    if body.model is not None:
        ac["model"] = body.model or None  # empty string → None (inherit)
    if body.max_cost is not None:
        ac["max_cost"] = body.max_cost
    if body.routing_weight is not None:
        ac["routing_weight"] = max(0.0, min(2.0, body.routing_weight))
    if body.enabled is not None:
        ac["enabled"] = body.enabled
    if body.timeout is not None:
        ac["timeout"] = max(30, body.timeout)

    save_config(config)
    return {"success": True, "config": ac}


@router.put("/{agent_name}/personality")
async def update_personality(agent_name: str, body: PersonalityUpdate):
    """Update agent personality prompt (writes personality.local.md)."""
    if agent_name not in AGENT_NAMES:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    home = get_cipher_home()
    local_path = home / "agents" / agent_name / "personality.local.md"
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(body.content)

    return {"success": True, "message": f"Prompt updated for {agent_name}"}


@router.delete("/{agent_name}/personality")
async def reset_personality(agent_name: str):
    """Reset agent personality to default (deletes local override)."""
    if agent_name not in AGENT_NAMES:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    home = get_cipher_home()
    local_path = home / "agents" / agent_name / "personality.local.md"
    if local_path.exists():
        local_path.unlink()

    return {"success": True, "message": f"Prompt reset to default for {agent_name}"}


@router.get("/{agent_name}/activity")
async def get_agent_activity(agent_name: str, limit: int = 20):
    """Get recent activity log entries for an agent."""
    if agent_name not in AGENT_NAMES:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    entries = query_activity(agent=agent_name, limit=limit)
    s = activity_stats(agent=agent_name)
    return {"entries": entries, "stats": s}

