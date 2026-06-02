"""Cross-agent communication — lightweight direct queries + heavy delegation."""

import time
from dataclasses import dataclass, field
from typing import Optional, Callable

from ..activity.log import log as activity_log


@dataclass
class DirectQuery:
    """A lightweight direct query between agents."""
    source_agent: str
    target_agent: str
    question: str
    context: str
    workspace: str
    timestamp: float = field(default_factory=time.time)
    response: Optional[str] = None
    timed_out: bool = False


@dataclass
class QueryTracker:
    """Tracks direct queries per task to enforce max_direct_per_task."""
    task_id: str
    agent: str
    queries: list[DirectQuery] = field(default_factory=list)
    max_queries: int = 3

    @property
    def remaining(self) -> int:
        return self.max_queries - len(self.queries)

    @property
    def exhausted(self) -> bool:
        return len(self.queries) >= self.max_queries


def can_query_direct(tracker: QueryTracker) -> tuple[bool, str]:
    """Check if an agent can still make direct queries for this task."""
    if tracker.exhausted:
        return False, (
            f"Direct query limit reached ({tracker.max_queries}/{tracker.max_queries}). "
            "Escalate to Cipher for further delegation."
        )
    return True, f"{tracker.remaining} direct queries remaining"


def create_query(
    source_agent: str,
    target_agent: str,
    question: str,
    context: str,
    workspace: str,
    tracker: Optional[QueryTracker] = None,
) -> DirectQuery:
    """Create a direct query between agents.

    Logs to activity_log. Enforces query limits via tracker.
    """
    # Check limits
    if tracker and tracker.exhausted:
        raise RuntimeError(
            f"Agent '{source_agent}' has exhausted direct queries for this task. "
            "Must escalate to Cipher."
        )

    query = DirectQuery(
        source_agent=source_agent,
        target_agent=target_agent,
        question=question,
        context=context,
        workspace=workspace,
    )

    # Log the query
    activity_log(
        workspace=workspace,
        agent=source_agent,
        model="system",
        task=f"Direct query to {target_agent}: {question[:100]}",
        status="running",
    )

    # Track
    if tracker:
        tracker.queries.append(query)

    return query


def complete_query(
    query: DirectQuery,
    response: str,
    workspace: str,
) -> DirectQuery:
    """Mark a direct query as completed with a response."""
    query.response = response

    activity_log(
        workspace=workspace,
        agent=query.target_agent,
        model="system",
        task=f"Answered query from {query.source_agent}: {query.question[:80]}",
        status="completed",
    )

    return query


def timeout_query(
    query: DirectQuery,
    workspace: str,
) -> DirectQuery:
    """Mark a direct query as timed out. Should escalate to Cipher."""
    query.timed_out = True

    activity_log(
        workspace=workspace,
        agent=query.source_agent,
        model="system",
        task=f"Query to {query.target_agent} timed out — escalating to Cipher",
        status="failed",
    )

    return query
