"""Ticket engine — SQLite-backed, per-workspace ticket boards."""

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..core.config import get_cipher_home


SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id TEXT PRIMARY KEY,
    workspace TEXT NOT NULL,
    project TEXT,
    title TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 3,
    status TEXT NOT NULL DEFAULT 'backlog',
    assigned_to TEXT,
    created_by TEXT NOT NULL,
    depends_on TEXT,
    blocks TEXT,
    tags TEXT,
    estimate TEXT,
    branch TEXT,
    pr_url TEXT,
    attempt_count INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    linear_id TEXT,
    linear_url TEXT,
    linear_identifier TEXT
);

CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_assigned ON tickets(assigned_to);
CREATE INDEX IF NOT EXISTS idx_tickets_priority ON tickets(priority);
CREATE INDEX IF NOT EXISTS idx_tickets_type ON tickets(type);
CREATE INDEX IF NOT EXISTS idx_tickets_project ON tickets(project);
CREATE INDEX IF NOT EXISTS idx_tickets_created_by ON tickets(created_by);

CREATE TABLE IF NOT EXISTS ticket_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id TEXT NOT NULL,
    field TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by TEXT NOT NULL,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
);

CREATE INDEX IF NOT EXISTS idx_history_ticket ON ticket_history(ticket_id);

CREATE TABLE IF NOT EXISTS ticket_counter (
    workspace TEXT PRIMARY KEY,
    counter INTEGER NOT NULL DEFAULT 0
);
"""

VALID_STATUSES = {"backlog", "ready", "in_progress", "review", "done", "blocked", "failed", "cancelled"}
VALID_TYPES = {"research", "planning", "development", "devops", "bug", "question"}
VALID_ESTIMATES = {"sm", "md", "lg", "xl"}


def get_db_path(workspace: str) -> Path:
    return get_cipher_home() / "workspaces" / workspace / "tickets" / "tickets.db"


def get_connection(workspace: str) -> sqlite3.Connection:
    """Get SQLite connection for a workspace's ticket board."""
    db_path = get_db_path(workspace)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    # migrate: add linear columns if missing (idempotent)
    existing = {r[1] for r in conn.execute("PRAGMA table_info(tickets)").fetchall()}
    for col, defn in [("linear_id", "TEXT"), ("linear_url", "TEXT"), ("linear_identifier", "TEXT")]:
        if col not in existing:
            conn.execute(f"ALTER TABLE tickets ADD COLUMN {col} {defn}")
    conn.commit()
    return conn


def _next_id(conn: sqlite3.Connection, workspace: str) -> str:
    """Generate next ticket ID (workspace-prefixed)."""
    prefix = workspace.upper()

    row = conn.execute(
        "SELECT counter FROM ticket_counter WHERE workspace = ?",
        (workspace,)
    ).fetchone()

    if row:
        next_num = row["counter"] + 1
        conn.execute(
            "UPDATE ticket_counter SET counter = ? WHERE workspace = ?",
            (next_num, workspace)
        )
    else:
        next_num = 1
        conn.execute(
            "INSERT INTO ticket_counter (workspace, counter) VALUES (?, ?)",
            (workspace, next_num)
        )

    return f"{prefix}-{next_num:03d}"


def create_ticket(
    workspace: str,
    title: str,
    type: str,
    created_by: str,
    project: Optional[str] = None,
    description: Optional[str] = None,
    priority: int = 3,
    assigned_to: Optional[str] = None,
    depends_on: Optional[list[str]] = None,
    tags: Optional[list[str]] = None,
    estimate: Optional[str] = None,
) -> dict:
    """Create a new ticket. Returns the ticket dict."""
    if type not in VALID_TYPES:
        raise ValueError(f"Invalid type '{type}'. Must be one of: {VALID_TYPES}")
    if estimate and estimate not in VALID_ESTIMATES:
        raise ValueError(f"Invalid estimate '{estimate}'. Must be one of: {VALID_ESTIMATES}")
    if priority < 1 or priority > 5:
        raise ValueError("Priority must be 1-5")

    conn = get_connection(workspace)
    now = datetime.now(timezone.utc).isoformat()
    ticket_id = _next_id(conn, workspace)

    # Check if blocked by dependencies
    status = "backlog"
    if depends_on:
        # Check if any dependency is incomplete
        for dep_id in depends_on:
            row = conn.execute("SELECT status FROM tickets WHERE id = ?", (dep_id,)).fetchone()
            if row and row["status"] not in ("done", "cancelled"):
                status = "blocked"
                break

    conn.execute(
        """INSERT INTO tickets
           (id, workspace, project, title, description, type, priority, status,
            assigned_to, created_by, depends_on, blocks, tags, estimate, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (ticket_id, workspace, project, title, description, type, priority, status,
         assigned_to, created_by,
         json.dumps(depends_on) if depends_on else None,
         None,
         json.dumps(tags) if tags else None,
         estimate, now, now),
    )

    # Update blocks field on dependencies
    if depends_on:
        for dep_id in depends_on:
            row = conn.execute("SELECT blocks FROM tickets WHERE id = ?", (dep_id,)).fetchone()
            if row:
                existing_blocks = json.loads(row["blocks"]) if row["blocks"] else []
                existing_blocks.append(ticket_id)
                conn.execute(
                    "UPDATE tickets SET blocks = ? WHERE id = ?",
                    (json.dumps(existing_blocks), dep_id)
                )

    conn.commit()
    ticket = dict(conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone())
    conn.close()
    return ticket


def update_ticket(
    workspace: str,
    ticket_id: str,
    changed_by: str,
    **fields,
) -> dict:
    """Update a ticket's fields. Logs changes to history."""
    conn = get_connection(workspace)
    now = datetime.now(timezone.utc).isoformat()

    current = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if not current:
        conn.close()
        raise ValueError(f"Ticket '{ticket_id}' not found")

    current = dict(current)
    updates = []
    params = []

    for field, value in fields.items():
        if field in ("id", "workspace", "created_by", "created_at"):
            continue  # Immutable fields

        old_value = current.get(field)

        # Serialize lists to JSON
        if isinstance(value, list):
            value = json.dumps(value)

        if str(old_value) != str(value):
            updates.append(f"{field} = ?")
            params.append(value)

            # Log to history
            conn.execute(
                """INSERT INTO ticket_history (ticket_id, field, old_value, new_value, changed_by, changed_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (ticket_id, field, str(old_value), str(value), changed_by, now),
            )

    if updates:
        updates.append("updated_at = ?")
        params.append(now)
        params.append(ticket_id)

        sql = f"UPDATE tickets SET {', '.join(updates)} WHERE id = ?"
        conn.execute(sql, params)

        # Handle status transitions
        new_status = fields.get("status")
        if new_status == "in_progress" and not current.get("started_at"):
            conn.execute("UPDATE tickets SET started_at = ? WHERE id = ?", (now, ticket_id))
        elif new_status in ("done", "cancelled"):
            conn.execute("UPDATE tickets SET completed_at = ? WHERE id = ?", (now, ticket_id))

            # Unblock dependent tickets
            if current.get("blocks"):
                blocked_ids = json.loads(current["blocks"]) if isinstance(current["blocks"], str) else current["blocks"]
                for blocked_id in (blocked_ids or []):
                    _check_unblock(conn, blocked_id)

    conn.commit()
    ticket = dict(conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone())
    conn.close()
    return ticket


def _check_unblock(conn: sqlite3.Connection, ticket_id: str):
    """Check if a blocked ticket can be unblocked (all deps done)."""
    row = conn.execute("SELECT depends_on, status FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if not row or row["status"] != "blocked":
        return

    depends = json.loads(row["depends_on"]) if row["depends_on"] else []
    all_done = True
    for dep_id in depends:
        dep = conn.execute("SELECT status FROM tickets WHERE id = ?", (dep_id,)).fetchone()
        if dep and dep["status"] not in ("done", "cancelled"):
            all_done = False
            break

    if all_done:
        conn.execute("UPDATE tickets SET status = 'ready' WHERE id = ?", (ticket_id,))


def query_tickets(
    workspace: str,
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    type: Optional[str] = None,
    priority: Optional[int] = None,
    project: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Query tickets with filters."""
    conn = get_connection(workspace)
    conditions = ["workspace = ?"]
    params: list = [workspace]

    if status:
        conditions.append("status = ?")
        params.append(status)
    if assigned_to:
        conditions.append("assigned_to = ?")
        params.append(assigned_to)
    if type:
        conditions.append("type = ?")
        params.append(type)
    if priority:
        conditions.append("priority = ?")
        params.append(priority)
    if project:
        conditions.append("project = ?")
        params.append(project)

    where = f"WHERE {' AND '.join(conditions)}"
    sql = f"""SELECT * FROM tickets {where}
             ORDER BY priority ASC, created_at ASC LIMIT ? OFFSET ?"""
    params.extend([limit, offset])

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_ticket(workspace: str, ticket_id: str) -> Optional[dict]:
    """Get a single ticket by ID."""
    conn = get_connection(workspace)
    row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_ticket_history(workspace: str, ticket_id: str) -> list[dict]:
    """Get change history for a ticket."""
    conn = get_connection(workspace)
    rows = conn.execute(
        "SELECT * FROM ticket_history WHERE ticket_id = ? ORDER BY changed_at ASC",
        (ticket_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Linear sync
# ---------------------------------------------------------------------------

LINEAR_PRIORITY_MAP = {1: 1, 2: 2, 3: 3, 4: 4, 0: 3}
LINEAR_STATE_MAP = {
    "backlog": "backlog",
    "unstarted": "backlog",
    "started": "in_progress",
    "in_progress": "in_progress",
    "in_review": "review",
    "review": "review",
    "done": "done",
    "completed": "done",
    "cancelled": "cancelled",
    "canceled": "cancelled",
}


def sync_from_linear(workspace: str, issues: list[dict]) -> dict:
    """Upsert Linear issues into the local ticket board.

    Returns {"created": N, "updated": N, "total": N}
    """
    conn = get_connection(workspace)
    created = 0
    updated = 0
    now = datetime.now(timezone.utc).isoformat()

    for issue in issues:
        linear_id = issue.get("id") or issue.get("identifier")
        if not linear_id:
            continue

        title = issue.get("title", "Untitled")
        priority = LINEAR_PRIORITY_MAP.get(issue.get("priority", 0), 3)
        state_raw = (issue.get("state") or {}).get("type", "backlog").lower()
        status = LINEAR_STATE_MAP.get(state_raw, "backlog")
        assignee = (issue.get("assignee") or {}).get("name")
        url = issue.get("url", "")
        identifier = issue.get("identifier", "")

        # check if already synced
        row = conn.execute(
            "SELECT id, status, title FROM tickets WHERE linear_id = ? AND workspace = ?",
            (linear_id, workspace)
        ).fetchone()

        if row:
            # update if anything changed
            conn.execute(
                """UPDATE tickets SET
                    title = ?, status = ?, priority = ?, assigned_to = ?,
                    linear_url = ?, linear_identifier = ?, updated_at = ?
                   WHERE linear_id = ? AND workspace = ?""",
                (title, status, priority, assignee, url, identifier, now, linear_id, workspace)
            )
            updated += 1
        else:
            # create new
            ticket_id = _next_id(conn, workspace)
            conn.execute(
                """INSERT INTO tickets
                    (id, workspace, title, type, priority, status, assigned_to, created_by,
                     linear_id, linear_url, linear_identifier, created_at, updated_at)
                   VALUES (?, ?, ?, 'task', ?, ?, ?, 'linear', ?, ?, ?, ?, ?)""",
                (ticket_id, workspace, title, priority, status, assignee,
                 linear_id, url, identifier, now, now)
            )
            created += 1

    conn.commit()
    conn.close()
    return {"created": created, "updated": updated, "total": len(issues)}
