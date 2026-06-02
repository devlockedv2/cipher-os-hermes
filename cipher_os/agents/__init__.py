"""Agent spawner — runs Hermes subprocesses for each agent with streaming output."""

import asyncio
import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncIterator, Optional

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

AGENT_COLORS = {
    "cipher": "#8B5CF6",
    "lens":   "#7DD3FC",
    "atlas":  "#5EE2B5",
    "forge":  "#F5B544",
    "sentinel": "#F26D6D",
}


@dataclass
class AgentSession:
    """Represents a running agent session."""
    agent: str
    workspace: str
    project: Optional[str] = None
    process: Optional[asyncio.subprocess.Process] = None
    status: str = "idle"  # idle | working | errored | dead
    current_task: Optional[str] = None
    ticket_id: Optional[str] = None
    allowed_paths: list[str] = field(default_factory=list)


def get_hermes_binary() -> str:
    """Find the Hermes binary from config or PATH."""
    home = get_cipher_home()
    config = load_config()

    # Check config first (written by installer)
    hermes_binary = config.get("hermes", {}).get("binary", "")
    if hermes_binary and Path(hermes_binary).is_file():
        return hermes_binary

    # Search PATH
    found = shutil.which("hermes")
    if found:
        return found

    # Common install locations
    for candidate in [
        Path.home() / ".local" / "bin" / "hermes",
        Path.home() / ".hermes" / "hermes-agent" / "hermes",
        Path("/usr/local/bin/hermes"),
    ]:
        if candidate.is_file():
            return str(candidate)

    raise RuntimeError(
        "Hermes Agent not found. Install it from https://github.com/NousResearch/hermes-agent "
        "or set hermes.binary in ~/.cipher-os/config.yaml"
    )


def get_agent_personality(agent: str) -> str:
    """Load agent personality (local override → installed → template)."""
    home = get_cipher_home()

    for path in [
        home / "agents" / agent / "personality.local.md",
        home / "agents" / agent / "personality.md",
        Path(__file__).parent.parent / "templates" / "agents" / agent / "personality.md",
    ]:
        if path.exists():
            return path.read_text()

    return f"# {agent.title()}\n\nYou are {agent.title()}, part of the CIPHER-OS agent fleet. {AGENT_ROLES.get(agent, '')}"


def get_rules() -> str:
    """Load safety + operations rules."""
    home = get_cipher_home()
    parts = []
    for name in ("safety.md", "operations.md"):
        p = home / "rules" / name
        if p.exists():
            parts.append(p.read_text())
    return "\n\n---\n\n".join(parts)


def build_system_prompt(agent: str, workspace: Optional[str] = None) -> str:
    """Build full system prompt: safety → ops → personality → workspace context."""
    parts = []

    rules = get_rules()
    if rules:
        parts.append(rules)

    parts.append(get_agent_personality(agent))

    if workspace:
        allowed = get_allowed_paths(workspace, agent)
        parts.append(
            f"## Session Context\n\n"
            f"- Workspace: {workspace}\n"
            f"- Agent: {agent}\n"
            f"- Allowed paths: {json.dumps(allowed)}\n"
            f"- Role: {AGENT_ROLES.get(agent, 'Unknown')}\n"
        )

    return "\n\n---\n\n".join(parts)


def build_hermes_cmd(
    agent: str,
    task: str,
    workspace: Optional[str] = None,
    model: Optional[str] = None,
) -> list[str]:
    """Build the hermes chat command for an agent task."""
    hermes = get_hermes_binary()
    config = load_config(workspace=workspace)

    # Model: explicit arg → per-agent config override → let Hermes use its own default
    agent_model = config.get("agents", {}).get(agent, {}).get("model") or model

    cmd = [hermes, "chat", "-q", task, "-Q"]  # -Q = quiet/programmatic

    if agent_model:
        cmd += ["-m", agent_model]
    # If no model specified, Hermes uses whatever is in its own config.yaml

    return cmd


def build_hermes_env(agent: str, workspace: Optional[str] = None) -> dict:
    """Build environment for the Hermes subprocess."""
    env = os.environ.copy()
    home = get_cipher_home()
    config = load_config(workspace=workspace)

    # Inject system prompt as HERMES_SYSTEM_PROMPT env var
    system_prompt = build_system_prompt(agent, workspace)
    env["HERMES_SYSTEM_PROMPT"] = system_prompt

    # Hermes home — use configured value if set, else let Hermes find its own
    hermes_home = config.get("hermes", {}).get("home", "")
    if hermes_home:
        env["HERMES_HOME"] = hermes_home

    # Workspace working directory
    if workspace:
        ws_path = home / "workspaces" / workspace
        ws_path.mkdir(parents=True, exist_ok=True)
        env["PWD"] = str(ws_path)

    return env


async def run_agent_streaming(
    agent: str,
    task: str,
    workspace: str = "default",
    model: Optional[str] = None,
) -> AsyncIterator[dict]:
    """
    Spawn a Hermes agent subprocess and stream output token by token.

    Yields dicts:
      {"type": "token",  "content": "..."}
      {"type": "done",   "content": ""}
      {"type": "error",  "content": "..."}
    """
    cmd = build_hermes_cmd(agent, task, workspace, model)
    env = build_hermes_env(agent, workspace)

    home = get_cipher_home()
    workdir = str(home / "workspaces" / workspace)
    Path(workdir).mkdir(parents=True, exist_ok=True)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=workdir,
        )

        # Stream stdout line by line
        assert proc.stdout
        buffer = ""
        async for chunk in _read_chunks(proc.stdout):
            buffer += chunk
            # Yield in reasonable token-sized pieces
            while len(buffer) >= 4:
                yield {"type": "token", "content": buffer[:64]}
                buffer = buffer[64:]

        # Flush remainder
        if buffer:
            yield {"type": "token", "content": buffer}

        # Wait for process to finish
        await proc.wait()

        # Grab stderr if non-zero exit
        stderr_data = b""
        if proc.returncode != 0:
            assert proc.stderr
            stderr_data = await proc.stderr.read()
            error_msg = stderr_data.decode("utf-8", errors="replace").strip()
            yield {"type": "error", "content": f"Agent exited with code {proc.returncode}: {error_msg}"}
        else:
            yield {"type": "done", "content": ""}

    except FileNotFoundError:
        yield {"type": "error", "content": "Hermes binary not found. Check installation."}
    except Exception as e:
        yield {"type": "error", "content": str(e)}


async def _read_chunks(stream: asyncio.StreamReader, chunk_size: int = 64) -> AsyncIterator[str]:
    """Read from an asyncio stream in chunks."""
    while True:
        try:
            chunk = await asyncio.wait_for(stream.read(chunk_size), timeout=120.0)
            if not chunk:
                break
            yield chunk.decode("utf-8", errors="replace")
        except asyncio.TimeoutError:
            break


def run_agent_sync(
    agent: str,
    task: str,
    workspace: str = "default",
    model: Optional[str] = None,
    timeout: int = 300,
) -> dict:
    """
    Blocking version — runs agent and returns full response.
    Used for ticket execution, not chat streaming.

    Returns: {"success": bool, "output": str, "error": str}
    """
    cmd = build_hermes_cmd(agent, task, workspace, model)
    env = build_hermes_env(agent, workspace)

    home = get_cipher_home()
    workdir = str(home / "workspaces" / workspace)
    Path(workdir).mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            cwd=workdir,
            timeout=timeout,
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout.strip(),
            "error": result.stderr.strip() if result.returncode != 0 else "",
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "", "error": f"Agent timed out after {timeout}s"}
    except FileNotFoundError:
        return {"success": False, "output": "", "error": "Hermes binary not found"}
    except Exception as e:
        return {"success": False, "output": "", "error": str(e)}


def get_agent_status() -> list[dict]:
    """Return status info for all agents, enriched from activity log."""
    from ..activity.log import stats as activity_stats
    config = load_config()
    agents = []
    for name in AGENT_NAMES:
        agent_config = config.get("agents", {}).get(name, {})
        s = activity_stats(agent=name)
        agents.append({
            "name": name,
            "role": AGENT_ROLES[name],
            "color": AGENT_COLORS[name],
            "model": agent_config.get("model") or config.get("hermes", {}).get("model", "default"),
            "status": "nominal",
            "tasks_completed": s.get("completed") or 0,
            "tasks_failed":    s.get("failed") or 0,
            "tasks_total":     s.get("total_tasks") or 0,
            "total_cost":      round(s.get("total_cost") or 0.0, 4),
            "input_tokens":    s.get("total_input_tokens") or 0,
            "output_tokens":   s.get("total_output_tokens") or 0,
        })
    return agents
