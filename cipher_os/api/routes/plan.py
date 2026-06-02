"""Plan route — task board view of the activity log."""

from fastapi import APIRouter, Query
from typing import Optional
from ...activity.log import query as activity_query, get_connection
from ...core.workspace import list_workspaces

router = APIRouter()


@router.get("/plan")
async def get_plan(workspace: Optional[str] = Query(None)):
    """Return tasks grouped by status for the kanban board."""
    rows = activity_query(workspace=workspace, limit=200)

    buckets: dict[str, list] = {
        "running": [],
        "pending": [],
        "completed": [],
        "failed": [],
    }

    for r in rows:
        status = r.get("status", "pending")
        bucket = status if status in buckets else "pending"
        buckets[bucket].append({
            "uuid": r["uuid"],
            "task": r["task"],
            "agent": r["agent"],
            "workspace": r["workspace"],
            "model": r.get("model", ""),
            "status": r["status"],
            "cost": r.get("cost", 0),
            "input_tokens": r.get("input_tokens", 0),
            "output_tokens": r.get("output_tokens", 0),
            "created_at": r["created_at"],
            "updated_at": r.get("updated_at", r["created_at"]),
        })

    workspaces = [ws["name"] for ws in list_workspaces()]

    return {
        "columns": [
            {"id": "running", "label": "Running", "color": "#06B6D4", "tasks": buckets["running"]},
            {"id": "pending", "label": "Pending", "color": "#8B5CF6", "tasks": buckets["pending"]},
            {"id": "completed", "label": "Completed", "color": "#10B981", "tasks": buckets["completed"]},
            {"id": "failed", "label": "Failed", "color": "#EF4444", "tasks": buckets["failed"]},
        ],
        "workspaces": workspaces,
        "total": len(rows),
    }
