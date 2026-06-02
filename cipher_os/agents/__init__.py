"""Agent spawner — connects to per-profile Hermes API Server gateways for real SSE streaming."""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncIterator, Optional

import httpx
import yaml

from ..core.config import get_cipher_home, load_config

logger = logging.getLogger(__name__)


AGENT_NAMES = ("cipher", "lens", "atlas", "forge", "sentinel")

AGENT_ROLES = {
    "cipher":   "Orchestrator — routes, delegates, approves",
    "lens":     "Researcher — deep research, source synthesis",
    "atlas":    "Planner — architecture, estimation, planning",
    "forge":    "Developer — code, tests, refactoring",
    "sentinel": "DevOps — infra, deploy, monitoring",
}

AGENT_COLORS = {
    "cipher":   "#8B5CF6",
    "lens":     "#7DD3FC",
    "atlas":    "#5EE2B5",
    "forge":    "#F5B544",
    "sentinel": "#F26D6D",
}

# Per-agent gateway ports (matches each profile's API_SERVER_PORT)
AGENT_PORTS = {
    "cipher":   8642,
    "lens":     8643,
    "atlas":    8644,
    "forge":    8645,
    "sentinel": 8646,
}

# Shared internal API key (set in each profile's .env as API_SERVER_KEY)
GATEWAY_API_KEY = "cipher-os-internal"


@dataclass
class AgentSession:
    """Represents a running agent session."""
    agent: str
    workspace: str
    project: Optional[str] = None
    session_id: Optional[str] = None
    status: str = "idle"   # idle | working | errored
    current_task: Optional[str] = None
    ticket_id: Optional[str] = None


def get_gateway_url(agent: str) -> str:
    """Return the base URL for an agent's gateway."""
    port = AGENT_PORTS.get(agent, 8642)
    return f"http://127.0.0.1:{port}"


def make_session_id(agent: str, workspace: str, ticket_id: Optional[str] = None) -> str:
    """
    Build a stable session ID.
    {agent}-{workspace}          → persistent workspace session (remembers context)
    {agent}-{workspace}-{ticket} → per-task isolated session
    """
    if ticket_id:
        return f"{agent}-{workspace}-{ticket_id}"
    return f"{agent}-{workspace}"


def _gateway_headers() -> dict:
    return {
        "Authorization": f"Bearer {GATEWAY_API_KEY}",
        "Content-Type": "application/json",
    }


async def gateway_health(agent: str) -> bool:
    """Check if an agent's gateway is reachable."""
    url = get_gateway_url(agent)
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{url}/health")
            return r.status_code == 200
    except Exception:
        return False


def _load_agent_personality(agent: str) -> str:
    """Load agent personality from Hermes profile config.yaml (agent.system_prompt)."""
    try:
        profile_cfg = Path.home() / ".hermes" / "profiles" / agent / "config.yaml"
        if profile_cfg.exists():
            with open(profile_cfg) as f:
                cfg = yaml.safe_load(f) or {}
            return str(cfg.get("agent", {}).get("system_prompt", "") or "").strip()
    except Exception:
        pass
    # Fallback: personality.md in cipher-os data dir
    try:
        p = get_cipher_home() / "agents" / agent / "personality.md"
        if p.exists():
            return p.read_text().strip()
    except Exception:
        pass
    return ""


async def _ensure_session(client: httpx.AsyncClient, agent: str, session_id: str) -> None:
    """Create the session if it doesn't exist yet."""
    url = get_gateway_url(agent)
    headers = _gateway_headers()
    r = await client.get(f"{url}/api/sessions/{session_id}", headers=headers)
    if r.status_code == 404:
        personality = _load_agent_personality(agent)
        payload: dict = {"id": session_id}
        if personality:
            payload["system_prompt"] = personality
        await client.post(f"{url}/api/sessions", headers=headers, json=payload)
        logger.info("[%s] Created session %s (personality: %d chars)", agent, session_id, len(personality))


async def run_agent_streaming(
    task: str,
    agent: str = "cipher",
    workspace: str = "default",
    ticket_id: Optional[str] = None,
    system_prompt_extra: Optional[str] = None,
) -> AsyncIterator[dict]:
    """
    Stream tokens from an agent's Hermes gateway via SSE.

    Yields dicts:
        {"type": "token",   "content": "..."}
        {"type": "done",    "content": ""}
        {"type": "error",   "content": "..."}

    SSE event format (Hermes-native):
        event: assistant.delta  → token chunk in data.delta
        event: assistant.completed → full response in data.content
        event: run.completed / done → stream end
        event: error → data.message
    """
    session_id = make_session_id(agent, workspace, ticket_id)
    url = get_gateway_url(agent)
    stream_url = f"{url}/api/sessions/{session_id}/chat/stream"

    # Always inject personality as per-call system_message override —
    # this ensures the agent uses the correct personality regardless of
    # what system_prompt was baked into the session at creation time.
    personality = _load_agent_personality(agent)
    payload: dict = {"message": task}
    if personality:
        payload["instructions"] = personality  # per-call system prompt override
    if system_prompt_extra:
        # Append extra context after personality
        payload["instructions"] = (payload.get("instructions", "") + "\n\n" + system_prompt_extra).strip()

    headers = _gateway_headers()
    headers["Accept"] = "text/event-stream"

    logger.info("[%s] SSE stream → session=%s", agent, session_id)

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
            # Ensure session exists before streaming
            await _ensure_session(client, agent, session_id)

            async with client.stream("POST", stream_url, json=payload, headers=headers) as resp:
                if resp.status_code not in (200, 201):
                    body = await resp.aread()
                    yield {"type": "error", "content": f"Gateway {resp.status_code}: {body.decode()[:200]}"}
                    return

                current_event = None
                buffer = ""

                async for chunk in resp.aiter_text():
                    buffer += chunk
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.rstrip()

                        if line.startswith("event:"):
                            current_event = line[6:].strip()
                            continue

                        if line.startswith("data:"):
                            data_str = line[5:].strip()
                            if not data_str or data_str == "[DONE]":
                                if current_event in ("done", "run.completed"):
                                    yield {"type": "done", "content": ""}
                                    return
                                continue

                            try:
                                data = json.loads(data_str)
                            except json.JSONDecodeError:
                                continue

                            if current_event == "assistant.delta":
                                delta = data.get("delta", "")
                                if delta:
                                    yield {"type": "token", "content": delta}

                            elif current_event == "done":
                                yield {"type": "done", "content": ""}
                                return

                            elif current_event == "run.completed":
                                # Hermes sends usage in run.completed payload
                                usage = data.get("usage") or {}
                                in_tok = usage.get("input_tokens", 0)
                                out_tok = usage.get("output_tokens", 0)
                                # Estimate cost: Sonnet ~$3/$15 per 1M tokens
                                est_cost = (in_tok * 3.0 + out_tok * 15.0) / 1_000_000
                                yield {
                                    "type": "done",
                                    "content": "",
                                    "input_tokens": in_tok,
                                    "output_tokens": out_tok,
                                    "cost": est_cost,
                                }
                                return

                            elif current_event == "error":
                                msg = data.get("message") or data.get("error", {}).get("message", "unknown error")
                                yield {"type": "error", "content": msg}
                                return

                            # Reset event after data
                            current_event = None

                        elif line == "":
                            # Blank line = end of SSE event block
                            current_event = None

        yield {"type": "done", "content": ""}

    except httpx.ConnectError:
        yield {"type": "error", "content": f"Agent '{agent}' gateway offline (port {AGENT_PORTS.get(agent)})"}
    except httpx.TimeoutException:
        yield {"type": "error", "content": f"Agent '{agent}' timed out after 120s"}
    except Exception as e:
        logger.exception("[%s] unexpected error", agent)
        yield {"type": "error", "content": str(e)}


async def run_agent_sync(task: str, agent: str = "cipher", workspace: str = "default") -> str:
    """Run agent and return full response as string (non-streaming)."""
    parts = []
    async for event in run_agent_streaming(task, agent=agent, workspace=workspace):
        if event["type"] == "token":
            parts.append(event["content"])
        elif event["type"] == "error":
            return f"[error] {event['content']}"
    return "".join(parts)


# ── Config & Status helpers ─────────────────────────────────────────────────

def get_agent_config(agent: str) -> dict:
    """Return per-agent config from ~/.cipher-os/config.yaml."""
    cfg = load_config()
    agents_cfg = cfg.get("agents", {})
    agent_cfg = agents_cfg.get(agent, {})
    return {
        "model": agent_cfg.get("model", ""),
        "max_cost": agent_cfg.get("max_cost", 5.0),
        "timeout": agent_cfg.get("timeout", 300),
        "routing_weight": agent_cfg.get("routing_weight", 1.0),
        "enabled": agent_cfg.get("enabled", True),
    }


def get_agent_personality(agent: str) -> str:
    """Return the current system prompt for an agent."""
    from pathlib import Path
    home = get_cipher_home()
    local_path = home / "agents" / agent / "personality.local.md"
    default_path = home / "agents" / agent / "personality.md"
    for p in (local_path, default_path):
        if p.exists():
            return p.read_text()
    return f"# {agent.capitalize()}\n\n{AGENT_ROLES.get(agent, '')}"


def get_agent_status() -> list:
    """Return status + stats for all agents."""
    try:
        from ..core.activity import stats as activity_stats
    except Exception:
        activity_stats = lambda **kw: {}

    result = []
    for agent in AGENT_NAMES:
        cfg = get_agent_config(agent)
        try:
            agent_stats = activity_stats(agent=agent)
        except Exception:
            agent_stats = {}
        result.append({
            "name": agent,
            "role": AGENT_ROLES[agent],
            "color": AGENT_COLORS[agent],
            "status": "online",
            "enabled": cfg["enabled"],
            "model": cfg["model"],
            "max_cost": cfg["max_cost"],
            "timeout": cfg["timeout"],
            "routing_weight": cfg["routing_weight"],
            "tasks_completed": agent_stats.get("completed", 0),
            "tasks_failed": agent_stats.get("failed", 0),
            "total_cost": agent_stats.get("total_cost", 0.0),
            "input_tokens": agent_stats.get("input_tokens", 0),
            "output_tokens": agent_stats.get("output_tokens", 0),
            "gateway_port": AGENT_PORTS[agent],
        })
    return result
