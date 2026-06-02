"""Tickets routes — CRUD for ticket boards."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ...tickets import (
    create_ticket, update_ticket, get_ticket,
    query_tickets, get_ticket_history,
)

router = APIRouter()


class TicketCreate(BaseModel):
    workspace: str
    title: str
    type: str
    created_by: str = "user"
    project: Optional[str] = None
    description: Optional[str] = None
    priority: int = 3
    assigned_to: Optional[str] = None
    depends_on: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    estimate: Optional[str] = None


class TicketUpdate(BaseModel):
    changed_by: str = "user"
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    priority: Optional[int] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    estimate: Optional[str] = None


@router.get("")
async def list_tickets(
    workspace: str,
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    type: Optional[str] = None,
    priority: Optional[int] = None,
    project: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """Query tickets with filters."""
    tickets = query_tickets(
        workspace=workspace,
        status=status,
        assigned_to=assigned_to,
        type=type,
        priority=priority,
        project=project,
        limit=limit,
        offset=offset,
    )
    return {"tickets": tickets, "total_count": len(tickets)}


@router.get("/{ticket_id}")
async def get_ticket_detail(ticket_id: str, workspace: str):
    """Get a single ticket with history."""
    ticket = get_ticket(workspace, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found")

    history = get_ticket_history(workspace, ticket_id)
    return {"ticket": ticket, "history": history}


@router.post("")
async def create_new_ticket(body: TicketCreate):
    """Create a new ticket."""
    try:
        ticket = create_ticket(
            workspace=body.workspace,
            title=body.title,
            type=body.type,
            created_by=body.created_by,
            project=body.project,
            description=body.description,
            priority=body.priority,
            assigned_to=body.assigned_to,
            depends_on=body.depends_on,
            tags=body.tags,
            estimate=body.estimate,
        )
        return ticket
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{ticket_id}")
async def patch_ticket(ticket_id: str, workspace: str, body: TicketUpdate):
    """Update a ticket's fields."""
    fields = body.model_dump(exclude_unset=True, exclude={"changed_by"})
    try:
        ticket = update_ticket(
            workspace=workspace,
            ticket_id=ticket_id,
            changed_by=body.changed_by,
            **fields,
        )
        return ticket
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{ticket_id}/history")
async def ticket_history(ticket_id: str, workspace: str):
    """Get change history for a ticket."""
    history = get_ticket_history(workspace, ticket_id)
    return history
