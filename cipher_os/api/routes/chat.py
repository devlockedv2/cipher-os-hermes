"""Chat routes — WebSocket streaming + REST fallback."""

import asyncio
import json
import re
import time
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from ...agents import run_agent_streaming, AGENT_NAMES
from ...core.config import load_config, get_cipher_home, get_linear_api_key
from ...activity.log import log as activity_log
from ...integrations.linear import (
    get_open_issues,
    create_issue as linear_create_issue,
    get_teams,
    format_issues_for_context,
)

router = APIRouter()


def _build_workspace_context(workspace: str) -> str:
    """
    Build an ephemeral context block injected into every Cipher session.
    Tells Cipher what workspace it's in, what workspaces exist, and the
    current open tickets so it can answer questions like 'what are my tickets'.
    """
    home = get_cipher_home()

    # List all workspaces
    ws_dir = home / "workspaces"
    workspaces = sorted(p.name for p in ws_dir.iterdir() if p.is_dir()) if ws_dir.exists() else [workspace]

    # Get open tickets for current workspace
    try:
        all_tickets = query_tickets(workspace=workspace)
        open_tickets = [t for t in all_tickets if t.get("status") not in ("done", "cancelled")]
    except Exception:
        open_tickets = []

    lines = [
        "## Current Session Context",
        f"- **Active workspace**: `{workspace}`",
        f"- **All workspaces**: {', '.join(f'`{w}`' for w in workspaces)}",
        "",
    ]

    if open_tickets:
        lines.append(f"## Open Tickets in `{workspace}` ({len(open_tickets)} open)")
        for t in open_tickets[:20]:  # cap at 20
            priority_map = {1: "critical", 2: "high", 3: "medium", 4: "low", 5: "minor"}
            pri = priority_map.get(t.get("priority", 3), "medium")
            assigned = t.get("assigned_to") or "unassigned"
            lines.append(
                f"- **{t['id']}** [{t['status']}] [{pri}] {t['title']} "
                f"(type: {t['type']}, assigned: {assigned})"
            )
    else:
        lines.append(f"## Tickets in `{workspace}`")
        lines.append("- No open tickets.")

    lines += [
        "",
        "Use this context to answer questions about workspaces and tickets directly.",
        "When the user asks about tickets, reference the list above.",
        "When creating tickets, use the active workspace unless told otherwise.",
    ]

    return "\n".join(lines)


async def _heartbeat(ws: WebSocket, interval: float = 4.0):
    """Send thinking heartbeats every `interval` seconds until cancelled.
    Keeps the WebSocket alive during slow Hermes subprocess startup (~20s)."""
    try:
        while True:
            await asyncio.sleep(interval)
            await ws.send_json({"type": "thinking"})
    except asyncio.CancelledError:
        pass
    except Exception:
        pass


# Markers Cipher outputs to trigger system actions
# [DELEGATE:agent:task description]
# [TICKET:type:title]
DELEGATE_RE = re.compile(r'\[DELEGATE:(\w+):([^\]]+)\]', re.IGNORECASE)
TICKET_RE   = re.compile(r'\[TICKET:([\w]+):([^\]]+)\]', re.IGNORECASE)
TICKETS_QUERY_RE = re.compile(r'\[TICKETS:([^\]]+)\]', re.IGNORECASE)


def _strip_markers(text: str) -> str:
    """Remove structural markers from text before sending to user."""
    text = DELEGATE_RE.sub('', text)
    text = TICKET_RE.sub('', text)
    text = TICKETS_QUERY_RE.sub('', text)
    return text.strip()


def _format_tickets_result(workspace: str) -> str:
    """Fetch Linear issues for workspace and return a compact context block."""
    api_key = get_linear_api_key(workspace)
    if not api_key:
        return (
            f"[TICKETS_RESULT: Linear not configured for workspace `{workspace}`. "
            "The user needs to add a Linear API key in workspace settings.]"
        )
    try:
        issues = get_open_issues(api_key, limit=30)
        return format_issues_for_context(issues, workspace)
    except Exception as e:
        return f"[TICKETS_RESULT: error fetching Linear issues — {e}]"


class ChatMessage(BaseModel):
    message: str
    workspace: str = "default"
    agent: Optional[str] = None  # force a specific agent (bypasses Cipher routing)


@router.websocket("/ws")
async def chat_websocket(ws: WebSocket):
    """
    WebSocket endpoint for streaming agent responses.

    All messages go to Cipher by default. Cipher handles them directly
    or emits delegation/ticket markers that the backend acts on.

    If the user explicitly selects an agent (agent != cipher), that agent
    is called directly with no routing layer.

    Client sends:
      {"message": "...", "workspace": "default", "agent": null}

    Server streams:
      {"type": "routing",   "agent": "cipher", "delegating_to": null}
      {"type": "token",     "content": "Hello..."}
      {"type": "delegating","agent": "lens",   "task": "..."}      -- when Cipher delegates
      {"type": "token",     "content": "..."}                       -- sub-agent stream
      {"type": "ticket_created", "ticket_id": "ALPHA-001"}          -- when ticket created
      {"type": "done",      "content": ""}
      {"type": "error",     "content": "..."}
    """
    await ws.accept()

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "content": "Invalid JSON"})
                continue

            message   = data.get("message", "").strip()
            workspace = data.get("workspace", "default")
            explicit_agent = data.get("agent")  # user explicitly picked an agent

            if not message:
                await ws.send_json({"type": "error", "content": "Empty message"})
                continue

            config = load_config(workspace=workspace)

            # --- Determine which agent to call first ---
            # If user picked a specific non-cipher agent, go direct (no routing layer).
            # Otherwise, always go to Cipher — Cipher decides what to do.
            primary_agent = explicit_agent if explicit_agent in AGENT_NAMES else "cipher"

            await ws.send_json({
                "type": "routing",
                "agent": primary_agent,
                "reason": "direct" if (explicit_agent and explicit_agent != "cipher") else "orchestrator",
                "direct": explicit_agent is not None and explicit_agent != "cipher",
            })

            # --- Stream primary agent (Cipher or explicit) ---
            start_time = time.time()
            full_response_parts = []
            total_input_tokens = 0
            total_output_tokens = 0
            total_cost = 0.0

            # Workspace context is NOT injected upfront — Cipher fetches tickets
            # on demand via [TICKETS:workspace] marker, keeping unrelated prompts lean.
            task_with_ctx = message

            # Send a heartbeat every 3 seconds while waiting for first token
            heartbeat_task = asyncio.create_task(_heartbeat(ws))

            try:
                async for event in run_agent_streaming(
                    agent=primary_agent,
                    task=task_with_ctx,
                    workspace=workspace,
                ):
                    if event["type"] == "token":
                        heartbeat_task.cancel()  # first token arrived — stop heartbeats
                        if primary_agent != "cipher":
                            # Non-cipher agents: stream directly, no marker interception needed
                            await ws.send_json({"type": "token", "content": event["content"]})
                        # For cipher: buffer silently — markers can span multiple tokens
                        full_response_parts.append(event["content"])
                    elif event["type"] == "done":
                        total_input_tokens += event.get("input_tokens", 0)
                        total_output_tokens += event.get("output_tokens", 0)
                        total_cost += event.get("cost", 0.0)
                        break
                    elif event["type"] == "error":
                        await ws.send_json(event)
                        break

            except Exception as e:
                heartbeat_task.cancel()
                await ws.send_json({"type": "error", "content": str(e)})

            full_response = "".join(full_response_parts)
            sent_done = False  # track whether we've sent done to the client

            # --- Parse Cipher's output for action markers ---
            if primary_agent == "cipher":
                # Handle [TICKETS:workspace] — Cipher wants to fetch tickets.
                # First pass was buffered silently. Now decide what to send.
                tickets_match = TICKETS_QUERY_RE.search(full_response)
                if tickets_match:
                    # Don't replay first-pass output at all — do a follow-up call
                    query_ws = tickets_match.group(1).strip() or workspace
                    result = _format_tickets_result(query_ws)
                    follow_up = f"[System: ticket query result]\n{result}\n\nNow answer the user's question using this data."
                    follow_parts = []
                    hb2 = asyncio.create_task(_heartbeat(ws))
                    try:
                        async for event in run_agent_streaming(
                            agent="cipher",
                            task=follow_up,
                            workspace=workspace,
                        ):
                            if event["type"] == "token":
                                hb2.cancel()
                                await ws.send_json({"type": "token", "content": event["content"]})
                                follow_parts.append(event["content"])
                            elif event["type"] == "done":
                                total_input_tokens += event.get("input_tokens", 0)
                                total_output_tokens += event.get("output_tokens", 0)
                                total_cost += event.get("cost", 0.0)
                                await ws.send_json({"type": "done", "content": ""})
                                sent_done = True
                                break
                            elif event["type"] == "error":
                                await ws.send_json(event)
                                sent_done = True
                                break
                    except Exception as e:
                        hb2.cancel()
                        await ws.send_json({"type": "error", "content": str(e)})
                        sent_done = True
                    full_response = "".join(follow_parts)
                else:
                    # No markers — replay the buffered cipher response to the client now
                    clean = _strip_markers(full_response)
                    if clean:
                        await ws.send_json({"type": "token", "content": clean})

                # Handle [TICKET:type:title] markers — Cipher decided work needs tracking
                for match in TICKET_RE.finditer(full_response):
                    ticket_type, ticket_title = match.group(1).lower(), match.group(2).strip()
                    api_key = get_linear_api_key(workspace)
                    if not api_key:
                        continue  # Linear not configured, skip silently
                    try:
                        # Get first available team for this workspace
                        teams = get_teams(api_key)
                        if not teams:
                            continue
                        team_id = teams[0]["id"]
                        issue = linear_create_issue(
                            api_key=api_key,
                            team_id=team_id,
                            title=ticket_title[:120],
                            description=f"*Created by Cipher*\n\nContext: {message[:300]}",
                            priority=3,  # medium
                        )
                        await ws.send_json({
                            "type": "ticket_created",
                            "ticket_id": issue.get("identifier", ""),
                            "title": ticket_title,
                            "url": issue.get("url", ""),
                        })
                    except Exception:
                        pass

                # Handle [DELEGATE:agent:task] markers — Cipher is delegating work
                for match in DELEGATE_RE.finditer(full_response):
                    sub_agent, sub_task = match.group(1).lower(), match.group(2).strip()
                    if sub_agent not in AGENT_NAMES or sub_agent == "cipher":
                        continue

                    await ws.send_json({
                        "type": "delegating",
                        "agent": sub_agent,
                        "task": sub_task,
                    })

                    sub_parts = []
                    try:
                        async for event in run_agent_streaming(
                            agent=sub_agent,
                            task=sub_task,
                            workspace=workspace,
                        ):
                            await ws.send_json(event)
                            if event["type"] == "token":
                                sub_parts.append(event["content"])
                            elif event["type"] in ("done", "error"):
                                break
                    except Exception as e:
                        await ws.send_json({"type": "error", "content": f"{sub_agent} error: {e}"})

                    # Log sub-agent activity
                    try:
                        activity_log(
                            workspace=workspace,
                            agent=sub_agent,
                            model=config.get("hermes", {}).get("model", "unknown"),
                            task=sub_task[:200],
                            status="completed" if sub_parts else "failed",
                        )
                    except Exception:
                        pass

            # --- Log primary agent activity ---
            try:
                activity_log(
                    workspace=workspace,
                    agent=primary_agent,
                    model=config.get("hermes", {}).get("model", "unknown"),
                    task=message[:200],
                    status="completed" if full_response else "failed",
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                    cost=total_cost,
                )
            except Exception:
                pass

            # Send final done if not already sent by ticket/delegate handlers
            if not sent_done:
                try:
                    await ws.send_json({"type": "done", "content": ""})
                except Exception:
                    pass

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_json({"type": "error", "content": str(e)})
        except Exception:
            pass


@router.post("")
async def send_chat(body: ChatMessage):
    """REST endpoint — returns routing decision. Used before opening WS."""
    agent = body.agent if body.agent in AGENT_NAMES else "cipher"
    return {
        "routing": {
            "agent": agent,
            "direct": body.agent is not None and body.agent != "cipher",
        }
    }
