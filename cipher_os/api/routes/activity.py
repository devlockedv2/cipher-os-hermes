"""Activity log routes — query and export activity."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from typing import Optional
import csv
import io

from ...activity.log import query as activity_query, stats as activity_stats

router = APIRouter()


@router.get("")
async def list_activity(
    workspace: Optional[str] = None,
    agent: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """Query activity log with filters."""
    entries = activity_query(
        workspace=workspace,
        agent=agent,
        status=status,
        limit=limit,
        offset=offset,
    )
    return {"entries": entries, "total_count": len(entries)}


@router.get("/stats")
async def get_activity_stats(
    workspace: Optional[str] = None,
    agent: Optional[str] = None,
):
    """Get aggregate stats."""
    return activity_stats(workspace=workspace, agent=agent)


@router.get("/export")
async def export_activity(
    workspace: Optional[str] = None,
    agent: Optional[str] = None,
):
    """Export activity log as CSV."""
    entries = activity_query(workspace=workspace, agent=agent, limit=10000)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "uuid", "workspace", "project", "agent", "model",
        "task", "status", "input_tokens", "output_tokens",
        "cost", "created_at",
    ])
    writer.writeheader()
    for entry in entries:
        writer.writerow({k: entry.get(k) for k in writer.fieldnames})

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=activity_export.csv"},
    )
