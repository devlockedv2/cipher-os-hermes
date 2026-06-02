"""Dashboard route — system overview."""

from fastapi import APIRouter

from ...activity.log import query as activity_query, stats as activity_stats
from ...core.workspace import list_workspaces
from ...agents import AGENT_NAMES, AGENT_ROLES, get_agent_status
from ...tickets import query_tickets

router = APIRouter()


def _count_active_tickets() -> int:
    """Count tickets not in terminal states across all workspaces."""
    workspaces = list_workspaces()
    total = 0
    for ws in workspaces:
        try:
            tickets = query_tickets(
                workspace=ws["name"],
                limit=1000,
            )
            total += sum(1 for t in tickets if t.get("status") not in ("done", "cancelled", "failed"))
        except Exception:
            pass
    return total


@router.get("/dashboard")
async def get_dashboard():
    """Get dashboard overview data."""
    workspaces = list_workspaces()
    recent_activity = activity_query(limit=20)
    global_stats = activity_stats()
    active_tickets = _count_active_tickets()

    # Live agent stats from activity log
    agents = []
    for a in get_agent_status():
        agents.append({
            "name": a["name"],
            "role": a["role"],
            "color": a["color"],
            "status": a.get("status", "idle"),
            "current_task": None,
            "workspace": None,
            "tasks_completed": a.get("tasks_completed", 0),
            "tasks_failed": a.get("tasks_failed", 0),
            "total_cost": a.get("total_cost", 0.0),
            "model": a.get("model", "default"),
            "enabled": a.get("enabled", True),
        })

    return {
        "agents": agents,
        "recent_activity": recent_activity,
        "active_tickets": active_tickets,
        "cost_today": global_stats.get("total_cost", 0),
        "workspaces": [{"name": ws["name"], "project_count": ws["project_count"]} for ws in workspaces],
        "stats": global_stats,
        "system_health": {
            "status": "nominal",
            "agents_active": sum(1 for a in agents if a.get("status") == "working"),
            "agents_total": len(AGENT_NAMES),
        },
    }
