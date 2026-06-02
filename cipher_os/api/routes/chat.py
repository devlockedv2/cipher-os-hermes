"""Chat routes — WebSocket streaming + REST fallback."""

import asyncio
import json
import re
import time
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from ...agents import run_agent_streaming, AGENT_NAMES
from ...core.config import load_config
from ...activity.log import log as activity_log
from ...tickets import create_ticket

router = APIRouter()

# Markers Cipher outputs to trigger system actions
# [DELEGATE:agent:task description]
# [TICKET:type:title]
DELEGATE_RE = re.compile(r'\[DELEGATE:(\w+):([^\]]+)\]', re.IGNORECASE)
TICKET_RE   = re.compile(r'\[TICKET:([\w]+):([^\]]+)\]', re.IGNORECASE)


def _strip_markers(text: str) -> str:
    """Remove structural markers from text before sending to user."""
    text = DELEGATE_RE.sub('', text)
    text = TICKET_RE.sub('', text)
    return text.strip()


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
                "direct": explicit_agent is not None and explicit_agent != "cipher",
            })

            # --- Stream primary agent (Cipher or explicit) ---
            start_time = time.time()
            full_response_parts = []

            try:
                async for event in run_agent_streaming(
                    agent=primary_agent,
                    task=message,
                    workspace=workspace,
                ):
                    if event["type"] == "token":
                        # Buffer to detect markers — send cleaned token to UI
                        cleaned = _strip_markers(event["content"])
                        if cleaned:
                            await ws.send_json({"type": "token", "content": cleaned})
                        full_response_parts.append(event["content"])  # keep raw for parsing
                    elif event["type"] in ("done", "error"):
                        await ws.send_json(event)
                        break

            except Exception as e:
                await ws.send_json({"type": "error", "content": str(e)})

            full_response = "".join(full_response_parts)

            # --- Parse Cipher's output for action markers ---
            if primary_agent == "cipher":
                # Handle [TICKET:type:title] markers — Cipher decided work needs tracking
                for match in TICKET_RE.finditer(full_response):
                    ticket_type, ticket_title = match.group(1).lower(), match.group(2).strip()
                    valid_types = {"research", "planning", "development", "devops", "bug", "question"}
                    if ticket_type not in valid_types:
                        ticket_type = "development"
                    try:
                        ticket = create_ticket(
                            workspace=workspace,
                            title=ticket_title[:120],
                            type=ticket_type,
                            created_by="cipher",
                            description=f"Created by Cipher from: {message[:200]}",
                        )
                        await ws.send_json({
                            "type": "ticket_created",
                            "ticket_id": ticket["id"],
                            "title": ticket_title,
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
                    status="completed" if full_response_parts else "failed",
                )
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
