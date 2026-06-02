"""Dashboard route — system overview with real metrics."""

from datetime import datetime, timezone, timedelta
from fastapi import APIRouter

from ...activity.log import query as activity_query, stats as activity_stats, get_connection
from ...core.workspace import list_workspaces
from ...agents import AGENT_NAMES, AGENT_ROLES, get_agent_status
import os

router = APIRouter()
_start_time = datetime.now(timezone.utc)


def _cost_today() -> float:
    """Sum cost from activity_log for entries created today (UTC)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = get_connection()
    row = conn.execute(
        "SELECT COALESCE(SUM(cost), 0) as c FROM activity_log WHERE created_at >= ?",
        (today,)
    ).fetchone()
    conn.close()
    return float(row["c"] if row else 0)


def _hourly_activity(hours: int = 24) -> list[dict]:
    """Return per-hour task counts + cost for the last N hours."""
    conn = get_connection()
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    rows = conn.execute(
        """SELECT
            strftime('%H', created_at) as hour,
            COUNT(*) as tasks,
            COALESCE(SUM(cost), 0) as cost
           FROM activity_log
           WHERE created_at >= ?
           GROUP BY strftime('%H', created_at)
           ORDER BY hour""",
        (since,)
    ).fetchall()
    conn.close()
    return [{"hour": r["hour"], "tasks": r["tasks"], "cost": round(float(r["cost"]), 4)} for r in rows]


def _agent_breakdown() -> list[dict]:
    """Per-agent aggregated stats."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT agent,
            COUNT(*) as total,
            SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed,
            COALESCE(SUM(input_tokens), 0) as input_tokens,
            COALESCE(SUM(output_tokens), 0) as output_tokens,
            COALESCE(SUM(cost), 0) as cost
           FROM activity_log
           GROUP BY agent"""
    ).fetchall()
    conn.close()
    return [{
        "agent": r["agent"],
        "total": r["total"],
        "completed": r["completed"],
        "failed": r["failed"],
        "input_tokens": r["input_tokens"],
        "output_tokens": r["output_tokens"],
        "cost": round(float(r["cost"]), 4),
    } for r in rows]


@router.get("/dashboard")
async def get_dashboard():
    workspaces = list_workspaces()
    recent_activity = activity_query(limit=20)
    global_stats = activity_stats()
    cost_today = _cost_today()
    hourly = _hourly_activity(24)
    agent_breakdown = _agent_breakdown()

    uptime_secs = int((datetime.now(timezone.utc) - _start_time).total_seconds())
    h, rem = divmod(uptime_secs, 3600)
    m, s = divmod(rem, 60)
    uptime_str = f"{h}h {m}m" if h else f"{m}m {s}s"

    # Live agent stats
    agents = []
    breakdown_map = {b["agent"]: b for b in agent_breakdown}
    for a in get_agent_status():
        bd = breakdown_map.get(a["name"], {})
        agents.append({
            "name": a["name"],
            "role": a["role"],
            "color": a["color"],
            "status": a.get("status", "idle"),
            "tasks_completed": bd.get("completed", a.get("tasks_completed", 0)),
            "tasks_failed": bd.get("failed", a.get("tasks_failed", 0)),
            "total_cost": bd.get("cost", a.get("total_cost", 0.0)),
            "input_tokens": bd.get("input_tokens", 0),
            "output_tokens": bd.get("output_tokens", 0),
            "model": a.get("model", "default"),
            "enabled": a.get("enabled", True),
        })

    total_tasks = int(global_stats.get("total_tasks") or 0)
    total_cost = float(global_stats.get("total_cost") or 0)
    total_in_tok = int(global_stats.get("total_input_tokens") or 0)
    total_out_tok = int(global_stats.get("total_output_tokens") or 0)

    return {
        "agents": agents,
        "recent_activity": recent_activity,
        "workspaces": [{"name": ws["name"], "project_count": ws["project_count"]} for ws in workspaces],
        "system_health": {
            "status": "nominal",
            "uptime": uptime_str,
            "agents_total": len(AGENT_NAMES),
            "agents_enabled": sum(1 for a in agents if a.get("enabled", True)),
        },
        "metrics": {
            "cost_today": round(cost_today, 4),
            "cost_alltime": round(total_cost, 4),
            "tasks_total": total_tasks,
            "tasks_completed": int(global_stats.get("completed") or 0),
            "tasks_failed": int(global_stats.get("failed") or 0),
            "input_tokens": total_in_tok,
            "output_tokens": total_out_tok,
            "total_tokens": total_in_tok + total_out_tok,
        },
        "hourly_activity": hourly,
        "agent_breakdown": agent_breakdown,
        # legacy keys for old UI components
        "active_tickets": 0,
        "cost_today": round(cost_today, 4),
        "stats": global_stats,
    }
