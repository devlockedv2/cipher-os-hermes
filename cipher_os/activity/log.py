"""Activity logging — SQLite-backed, self-logging by agents."""

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..core.config import get_cipher_home


SCHEMA = """
CREATE TABLE IF NOT EXISTS activity_log (
    uuid TEXT PRIMARY KEY,
    workspace TEXT NOT NULL,
    project TEXT,
    agent TEXT NOT NULL,
    model TEXT NOT NULL,
    task TEXT NOT NULL,
    status TEXT NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost REAL DEFAULT 0.0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_activity_workspace ON activity_log(workspace);
CREATE INDEX IF NOT EXISTS idx_activity_project ON activity_log(project);
CREATE INDEX IF NOT EXISTS idx_activity_agent ON activity_log(agent);
CREATE INDEX IF NOT EXISTS idx_activity_status ON activity_log(status);
CREATE INDEX IF NOT EXISTS idx_activity_created_at ON activity_log(created_at);
CREATE INDEX IF NOT EXISTS idx_activity_workspace_agent ON activity_log(workspace, agent);
CREATE INDEX IF NOT EXISTS idx_activity_workspace_project ON activity_log(workspace, project);
"""


def get_db_path() -> Path:
    return get_cipher_home() / "activity.db"


def get_connection() -> sqlite3.Connection:
    """Get SQLite connection, creating schema if needed."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def log(
    workspace: str,
    agent: str,
    model: str,
    task: str,
    status: str,
    project: Optional[str] = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost: float = 0.0,
    entry_uuid: Optional[str] = None,
) -> str:
    """Log an activity entry. Returns the UUID.

    For single responses: call once with status='completed' or 'failed'.
    For multi-step: call with status='running', then update with the returned UUID.
    """
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()

    if entry_uuid:
        # Update existing entry
        conn.execute(
            """UPDATE activity_log
               SET status = ?, input_tokens = ?, output_tokens = ?, cost = ?, updated_at = ?
               WHERE uuid = ?""",
            (status, input_tokens, output_tokens, cost, now, entry_uuid),
        )
        conn.commit()
        conn.close()
        return entry_uuid

    # New entry
    entry_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO activity_log
           (uuid, workspace, project, agent, model, task, status,
            input_tokens, output_tokens, cost, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (entry_id, workspace, project, agent, model, task, status,
         input_tokens, output_tokens, cost, now, now),
    )
    conn.commit()
    conn.close()
    return entry_id


def query(
    workspace: Optional[str] = None,
    agent: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Query activity log with filters."""
    conn = get_connection()
    conditions = []
    params = []

    if workspace:
        conditions.append("workspace = ?")
        params.append(workspace)
    if agent:
        conditions.append("agent = ?")
        params.append(agent)
    if status:
        conditions.append("status = ?")
        params.append(status)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"""SELECT * FROM activity_log {where}
             ORDER BY created_at DESC LIMIT ? OFFSET ?"""
    params.extend([limit, offset])

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def stats(
    workspace: Optional[str] = None,
    agent: Optional[str] = None,
) -> dict:
    """Get aggregate stats (total tokens, cost)."""
    conn = get_connection()
    conditions = []
    params = []

    if workspace:
        conditions.append("workspace = ?")
        params.append(workspace)
    if agent:
        conditions.append("agent = ?")
        params.append(agent)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"""SELECT
        COUNT(*) as total_tasks,
        SUM(input_tokens) as total_input_tokens,
        SUM(output_tokens) as total_output_tokens,
        SUM(cost) as total_cost,
        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
    FROM activity_log {where}"""

    row = conn.execute(sql, params).fetchone()
    conn.close()
    return dict(row) if row else {}
