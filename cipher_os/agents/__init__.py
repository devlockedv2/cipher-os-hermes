"""Agent spawner — creates and manages Hermes profile sessions for agents."""

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..core.config import get_cipher_home, load_config
from ..core.workspace import get_allowed_paths


AGENT_NAMES = ("cipher", "lens", "atlas", "forge", "sentinel")

AGENT_ROLES = {
    "cipher": "Orchestrator — routes, delegates, approves",
    "lens": "Researcher — deep research, source synthesis",
    "atlas": "Planner — architecture, estimation, planning",
    "forge": "Developer — code, tests, refactoring",
    "sentinel": "DevOps — infra, deploy, monitoring",
}


@dataclass
class AgentSession:
    """Represents a running agent session."""
    agent: str
    workspace: str
    project: Optional[str] = None
    process: Optional[subprocess.Popen] = None
    status: str = "idle"  # idle | working | errored | dead
    current_task: Optional[str] = None
    ticket_id: Optional[str] = None
    allowed_paths: list[str] = field(default_factory=list)


def get_agent_personality(agent: str) -> str:
    """Load agent personality (local override or default template)."""
    home = get_cipher_home()

    # Check for user-edited local override
    local_path = home / "agents" / agent / "personality.local.md"
    if local_path.exists():
        return local_path.read_text()

    # Fall back to installed personality
    default_path = home / "agents" / agent / "personality.md"
    if default_path.exists():
        return default_path.read_text()

    # Fall back to template (pre-install)
    template_path = Path(__file__).parent.parent.parent / "templates" / "agents" / agent / "personality.md"
    if template_path.exists():
        return template_path.read_text()

    return f"# {agent.title()}\n\nAgent personality not configured."


def get_rules() -> str:
    """Load rules in correct order: safety first, then operations."""
    home = get_cipher_home()
    parts = []

    safety_path = home / "rules" / "safety.md"
    if safety_path.exists():
        parts.append(safety_path.read_text())

    ops_path = home / "rules" / "operations.md"
    if ops_path.exists():
        parts.append(ops_path.read_text())

    return "\n\n---\n\n".join(parts)


def get_knowledge(workspace: Optional[str] = None) -> str:
    """Load knowledge files: global + workspace-specific."""
    home = get_cipher_home()
    parts = []

    # Global knowledge
    global_kb = home / "knowledge"
    if global_kb.exists():
        for f in sorted(global_kb.glob("*.md")):
            parts.append(f.read_text())

    # Workspace knowledge
    if workspace:
        ws_kb = home / "workspaces" / workspace / "knowledge"
        if ws_kb.exists():
            for f in sorted(ws_kb.glob("*.md")):
                parts.append(f.read_text())

    return "\n\n---\n\n".join(parts)


def build_system_prompt(agent: str, workspace: Optional[str] = None) -> str:
    """Build the full system prompt for an agent.

    Load order:
    1. safety.md (absolute constraints — FIRST)
    2. operations.md (how to work)
    3. personality.md (who you are)
    4. knowledge/ (shared context)
    5. workspace context (scoping info)
    """
    parts = []

    # 1 + 2: Rules
    rules = get_rules()
    if rules:
        parts.append(rules)

    # 3: Personality
    personality = get_agent_personality(agent)
    parts.append(personality)

    # 4: Knowledge
    knowledge = get_knowledge(workspace)
    if knowledge:
        parts.append(knowledge)

    # 5: Workspace context
    if workspace:
        allowed = get_allowed_paths(workspace, agent)
        context = f"""## Session Context

- Workspace: {workspace}
- Agent: {agent}
- Allowed paths: {json.dumps(allowed)}
- Role: {AGENT_ROLES.get(agent, 'Unknown')}
"""
        parts.append(context)

    return "\n\n---\n\n".join(parts)


def get_agent_model(agent: str, workspace: Optional[str] = None) -> Optional[str]:
    """Get the model for an agent (per-agent override or workspace/global default)."""
    config = load_config(workspace=workspace)
    agent_config = config.get("agents", {}).get(agent, {})
    return agent_config.get("model")  # None = use system default
