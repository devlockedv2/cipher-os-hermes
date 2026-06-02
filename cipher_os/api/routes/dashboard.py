"""Dashboard route — system overview."""

from fastapi import APIRouter

from ...activity.log import query as activity_query, stats as activity_stats
from ...core.workspace import list_workspaces
from ...agents import AGENT_NAMES, AGENT_ROLES

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard():
    """Get dashboard overview data."""
    workspaces = list_workspaces()
    recent_activity = activity_query(limit=20)
    global_stats = activity_stats()

    # Agent statuses (placeholder — will be live when spawner is integrated)
    agents = [
        {
            "name": name,
            "role": AGENT_ROLES[name],
            "status": "idle",
            "current_task": None,
            "workspace": None,
        }
        for name in AGENT_NAMES
    ]

    return {
        "agents": agents,
        "recent_activity": recent_activity,
        "workspaces": [{"name": ws["name"], "project_count": ws["project_count"]} for ws in workspaces],
        "stats": global_stats,
        "system_health": {
            "status": "nominal",
            "agents_active": 0,
            "agents_total": len(AGENT_NAMES),
        },
    }
