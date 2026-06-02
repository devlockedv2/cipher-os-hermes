"""Chat routes — WebSocket streaming + REST fallback."""

import asyncio
import json
import time
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from ...agents import run_agent_streaming, get_agent_status
from ...agents.orchestrator import route_task, approve_plan, decompose_task
from ...core.config import load_config
from ...activity.log import log as activity_log
from ...tickets import create_ticket, update_ticket

router = APIRouter()


class ChatMessage(BaseModel):
    message: str
    workspace: str = "default"
    agent: Optional[str] = None  # force a specific agent


@router.post("")
async def send_chat(body: ChatMessage):
    """
    REST endpoint — routes task, returns routing decision synchronously.
    Used by the UI before opening a WebSocket for streaming.
    """
    config = load_config(workspace=body.workspace)
    mode = config.get("routing", {}).get("mode", "supervised")

    routing = route_task(
        task_description=body.message,
        workspace=body.workspace,
        explicit_agent=body.agent,
    )
    approval = approve_plan(body.message, routing, mode=mode)

    return {
        "routing": {
            "agent": routing.agent,
            "type": routing.task_type,
            "confidence": routing.confidence,
            "reason": routing.reason,
            "needs_decomposition": routing.needs_decomposition,
            "is_destructive": routing.is_destructive,
        },
        "approval": approval,
    }


@router.websocket("/ws")
async def chat_websocket(ws: WebSocket):
    """
    WebSocket endpoint for streaming agent responses.

    Client sends:
      {"message": "...", "workspace": "default", "agent": null}

    Server streams:
      {"type": "routing",  "agent": "forge", "reason": "..."}
      {"type": "token",    "content": "Hello..."}
      {"type": "done",     "content": ""}
      {"type": "error",    "content": "..."}
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

            message = data.get("message", "").strip()
            workspace = data.get("workspace", "default")
            explicit_agent = data.get("agent")

            if not message:
                await ws.send_json({"type": "error", "content": "Empty message"})
                continue

            # Route the task
            config = load_config(workspace=workspace)
            mode = config.get("routing", {}).get("mode", "supervised")

            routing = route_task(
                task_description=message,
                workspace=workspace,
                explicit_agent=explicit_agent,
            )
            approval = approve_plan(message, routing, mode=mode)

            # Send routing decision first
            await ws.send_json({
                "type": "routing",
                "agent": routing.agent,
                "task_type": routing.task_type,
                "reason": routing.reason,
                "approved": approval["approved"],
            })

            # Destructive / unapproved — stop and ask user
            if not approval["approved"]:
                await ws.send_json({
                    "type": "blocked",
                    "content": approval["reason"],
                    "escalate_to": approval.get("escalate_to"),
                })
                continue

            # Create a ticket to track this task
            try:
                ticket = create_ticket(
                    workspace=workspace,
                    title=message[:120],
                    type=routing.task_type,
                    created_by="user",
                    assigned_to=routing.agent,
                    description=message,
                    estimate="sm",
                )
                ticket_id = ticket["id"]
                await ws.send_json({"type": "ticket", "ticket_id": ticket_id})
            except Exception:
                ticket_id = None

            # Stream the agent response
            start_time = time.time()
            full_response = []

            try:
                async for event in run_agent_streaming(
                    agent=routing.agent,
                    task=message,
                    workspace=workspace,
                ):
                    await ws.send_json(event)
                    if event["type"] == "token":
                        full_response.append(event["content"])
                    elif event["type"] in ("done", "error"):
                        break

            except Exception as e:
                await ws.send_json({"type": "error", "content": str(e)})

            # Log activity
            elapsed = time.time() - start_time
            try:
                activity_log(
                    workspace=workspace,
                    agent=routing.agent,
                    model=config.get("hermes", {}).get("model", "unknown"),
                    task=message[:200],
                    status="completed" if full_response else "failed",
                )
            except Exception:
                pass

            # Update ticket to done
            if ticket_id:
                try:
                    update_ticket(workspace, ticket_id, changed_by="cipher", status="done")
                except Exception:
                    pass

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_json({"type": "error", "content": str(e)})
        except Exception:
            pass
