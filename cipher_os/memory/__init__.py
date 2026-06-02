"""Memory engine — SQLite+FTS5 with markdown view layer."""

import sqlite3
import json
import uuid
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..core.config import get_cipher_home


SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    agent TEXT NOT NULL,
    scope TEXT NOT NULL,
    category TEXT,
    content TEXT NOT NULL,
    source_session TEXT,
    created_at TIMESTAMP NOT NULL,
    last_accessed TIMESTAMP NOT NULL,
    access_count INTEGER DEFAULT 0,
    pinned BOOLEAN DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_memories_agent ON memories(agent);
CREATE INDEX IF NOT EXISTS idx_memories_scope ON memories(scope);
CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
CREATE INDEX IF NOT EXISTS idx_memories_pinned ON memories(pinned);

CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    content,
    agent,
    scope,
    category,
    content=memories,
    content_rowid=rowid,
    tokenize='porter'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, content, agent, scope, category)
    VALUES (new.rowid, new.content, new.agent, new.scope, new.category);
END;

CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content, agent, scope, category)
    VALUES ('delete', old.rowid, old.content, old.agent, old.scope, old.category);
END;

CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content, agent, scope, category)
    VALUES ('delete', old.rowid, old.content, old.agent, old.scope, old.category);
    INSERT INTO memories_fts(rowid, content, agent, scope, category)
    VALUES (new.rowid, new.content, new.agent, new.scope, new.category);
END;
"""

VALID_CATEGORIES = {"pattern", "fact", "preference", "decision", "convention", "lesson"}
VALID_SCOPES = {"profile", "workspace"}


def get_db_path(scope: str = "profile", workspace: Optional[str] = None) -> Path:
    """Get the memory DB path based on scope."""
    home = get_cipher_home()
    if scope == "workspace" and workspace:
        return home / "workspaces" / workspace / "memories" / "memories.db"
    return home / "memories.db"


def get_connection(scope: str = "profile", workspace: Optional[str] = None) -> sqlite3.Connection:
    """Get SQLite connection for memory DB."""
    db_path = get_db_path(scope, workspace)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def add(
    agent: str,
    content: str,
    scope: str = "profile",
    workspace: Optional[str] = None,
    category: Optional[str] = None,
    source_session: Optional[str] = None,
    pinned: bool = False,
) -> str:
    """Add a memory entry. Returns the memory ID."""
    if category and category not in VALID_CATEGORIES:
        raise ValueError(f"Invalid category '{category}'. Must be one of: {VALID_CATEGORIES}")

    scope_value = f"workspace:{workspace}" if scope == "workspace" and workspace else "profile"
    conn = get_connection(scope, workspace)
    now = datetime.now(timezone.utc).isoformat()
    memory_id = str(uuid.uuid4())

    conn.execute(
        """INSERT INTO memories
           (id, agent, scope, category, content, source_session, created_at, last_accessed, access_count, pinned)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
        (memory_id, agent, scope_value, category, content, source_session, now, now, int(pinned)),
    )
    conn.commit()
    conn.close()

    # Sync to markdown
    _export_markdown(scope, workspace)

    return memory_id


def search(
    query: str,
    agent: Optional[str] = None,
    scope: str = "profile",
    workspace: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """Full-text search across memories using FTS5."""
    conn = get_connection(scope, workspace)

    # Build FTS5 query
    conditions = []
    if agent:
        conditions.append(f"agent:{agent}")

    fts_query = query
    if conditions:
        fts_query = f"{query} {' '.join(conditions)}"

    sql = """
        SELECT m.*, rank
        FROM memories m
        JOIN memories_fts ON m.rowid = memories_fts.rowid
        WHERE memories_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """

    try:
        rows = conn.execute(sql, (fts_query, limit)).fetchall()
    except sqlite3.OperationalError:
        # FTS5 query syntax error — fall back to simple LIKE
        rows = conn.execute(
            "SELECT *, 0 as rank FROM memories WHERE content LIKE ? LIMIT ?",
            (f"%{query}%", limit),
        ).fetchall()

    # Update access counts
    for row in rows:
        conn.execute(
            "UPDATE memories SET access_count = access_count + 1, last_accessed = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), row["id"]),
        )
    conn.commit()
    conn.close()

    return [dict(row) for row in rows]


def get_all(
    agent: Optional[str] = None,
    scope: str = "profile",
    workspace: Optional[str] = None,
    category: Optional[str] = None,
) -> list[dict]:
    """Get all memories for an agent (optionally filtered by category)."""
    conn = get_connection(scope, workspace)
    conditions = []
    params = []

    if agent:
        conditions.append("agent = ?")
        params.append(agent)
    if category:
        conditions.append("category = ?")
        params.append(category)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = conn.execute(
        f"SELECT * FROM memories {where} ORDER BY pinned DESC, last_accessed DESC",
        params,
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def remove(
    memory_id: str,
    scope: str = "profile",
    workspace: Optional[str] = None,
) -> bool:
    """Remove a memory entry. Pinned memories cannot be removed."""
    conn = get_connection(scope, workspace)

    row = conn.execute("SELECT pinned FROM memories WHERE id = ?", (memory_id,)).fetchone()
    if not row:
        conn.close()
        return False
    if row["pinned"]:
        conn.close()
        raise ValueError("Cannot remove pinned memory. Unpin first.")

    conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    conn.commit()
    conn.close()

    _export_markdown(scope, workspace)
    return True


def pin(memory_id: str, scope: str = "profile", workspace: Optional[str] = None) -> bool:
    """Pin a memory (prevents pruning/removal)."""
    conn = get_connection(scope, workspace)
    conn.execute("UPDATE memories SET pinned = 1 WHERE id = ?", (memory_id,))
    conn.commit()
    conn.close()
    return True


def unpin(memory_id: str, scope: str = "profile", workspace: Optional[str] = None) -> bool:
    """Unpin a memory."""
    conn = get_connection(scope, workspace)
    conn.execute("UPDATE memories SET pinned = 0 WHERE id = ?", (memory_id,))
    conn.commit()
    conn.close()
    return True


def prune(
    max_age_days: int = 90,
    min_access_count: int = 0,
    scope: str = "profile",
    workspace: Optional[str] = None,
) -> int:
    """Prune low-use, old memories. Pinned memories are never pruned.

    Returns count of pruned entries.
    """
    conn = get_connection(scope, workspace)
    cutoff = datetime.now(timezone.utc).isoformat()

    result = conn.execute(
        """DELETE FROM memories
           WHERE pinned = 0
             AND access_count <= ?
             AND julianday(?) - julianday(last_accessed) > ?""",
        (min_access_count, cutoff, max_age_days),
    )
    count = result.rowcount
    conn.commit()
    conn.close()

    if count > 0:
        _export_markdown(scope, workspace)

    return count


def _export_markdown(scope: str = "profile", workspace: Optional[str] = None):
    """Export memories to markdown files (bidirectional sync — DB → markdown)."""
    home = get_cipher_home()

    if scope == "workspace" and workspace:
        md_dir = home / "workspaces" / workspace / "memories"
    else:
        md_dir = home / "memories_md"

    md_dir.mkdir(parents=True, exist_ok=True)

    memories = get_all(scope=scope, workspace=workspace)

    # Group by agent
    by_agent: dict[str, list[dict]] = {}
    for mem in memories:
        agent = mem["agent"]
        if agent not in by_agent:
            by_agent[agent] = []
        by_agent[agent].append(mem)

    # Write one markdown file per agent
    for agent, mems in by_agent.items():
        lines = [f"# {agent.title()} — Memories\n"]

        for mem in mems:
            pin_marker = " 📌" if mem.get("pinned") else ""
            category = f" [{mem['category']}]" if mem.get("category") else ""
            lines.append(f"## {mem['id'][:8]}{category}{pin_marker}\n")
            lines.append(f"{mem['content']}\n")
            lines.append(f"*Last accessed: {mem['last_accessed']} | Uses: {mem['access_count']}*\n")
            lines.append("")

        (md_dir / f"{agent}.md").write_text("\n".join(lines))
