"""Chat routes — send messages to Cipher (Orchestrator)."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from ...agents.orchestrator import route_task, approve_plan, decompose_task
from ...core.config import load_config

router = APIRouter()


class ChatMessage(BaseModel):
    message: str
    workspace: str = "default"


@router.post("")
async def send_chat(body: ChatMessage):
    """Send a message to the Orchestrator.

    In full implementation, this spawns Cipher and streams via WebSocket.
    For now, returns the routing decision Cipher would make.
    """
    config = load_config(workspace=body.workspace)
    mode = config.get("routing", {}).get("mode", "supervised")

    # Route the task
    routing = route_task(
        task_description=body.message,
        workspace=body.workspace,
    )

    # Check approval
    approval = approve_plan(body.message, routing, mode=mode)

    response = {
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

    # If compound, show decomposition plan
    if routing.needs_decomposition and approval["approved"]:
        response["decomposition_plan"] = [
            {"type": t, "agent": a}
            for t, a in [
                ("research", "lens"),
                ("planning", "atlas"),
                ("development", "forge"),
                ("devops", "sentinel"),
            ]
            if t in body.message.lower() or any(
                kw in body.message.lower()
                for kw in ["build", "implement", "deploy", "research", "plan"]
            )
        ]

    return response
