"""Error recovery and watchdog — handles agent crashes, timeouts, retries."""

import time
from dataclasses import dataclass, field
from typing import Optional

from ..activity.log import log as activity_log
from ..tickets import update_ticket


@dataclass
class Checkpoint:
    """Agent progress checkpoint for crash recovery."""
    ticket_id: str
    workspace: str
    agent: str
    progress: str
    artifacts: list[str] = field(default_factory=list)
    next_step: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class HealthStatus:
    """Agent health status."""
    agent: str
    alive: bool
    last_heartbeat: float
    consecutive_failures: int = 0
    status: str = "healthy"  # healthy | degraded | dead


# Time limits by estimate size (minutes)
TIME_LIMITS = {
    "sm": 15,
    "md": 60,
    "lg": 180,
    "xl": 480,
}


def check_timeout(started_at: float, estimate: str = "md") -> tuple[bool, int]:
    """Check if a task has exceeded its time limit.

    Returns: (timed_out: bool, elapsed_minutes: int)
    """
    limit = TIME_LIMITS.get(estimate, 60)
    elapsed = (time.time() - started_at) / 60.0
    return elapsed > limit, int(elapsed)


def should_retry(
    attempt_count: int,
    max_attempts: int = 3,
    is_destructive: bool = False,
) -> tuple[bool, str]:
    """Determine if a failed task should be retried.

    Returns: (should_retry: bool, reason: str)
    """
    if is_destructive:
        return False, "Destructive actions are never auto-retried"

    if attempt_count >= max_attempts:
        return False, f"Max attempts reached ({attempt_count}/{max_attempts}) — escalating to user"

    return True, f"Retrying (attempt {attempt_count + 1}/{max_attempts})"


def handle_agent_failure(
    workspace: str,
    ticket_id: str,
    agent: str,
    failure_type: str,  # "crash" | "timeout" | "error"
    error_message: str = "",
    is_destructive: bool = False,
    max_attempts: int = 3,
) -> dict:
    """Handle an agent failure — decide retry vs escalate.

    Returns: {action: 'retry' | 'escalate', reason: str, attempt: int}
    """
    # Update ticket
    ticket = update_ticket(
        workspace=workspace,
        ticket_id=ticket_id,
        changed_by="system",
        status="failed",
    )

    attempt_count = (ticket.get("attempt_count", 0) or 0) + 1
    update_ticket(
        workspace=workspace,
        ticket_id=ticket_id,
        changed_by="system",
        attempt_count=attempt_count,
    )

    # Log failure
    activity_log(
        workspace=workspace,
        agent=agent,
        model="system",
        task=f"{failure_type.upper()}: {error_message[:100]}" if error_message else f"{failure_type.upper()} on {ticket_id}",
        status="failed",
    )

    # Decide retry
    retry, reason = should_retry(attempt_count, max_attempts, is_destructive)

    if retry:
        return {
            "action": "retry",
            "reason": reason,
            "attempt": attempt_count,
            "ticket_id": ticket_id,
        }
    else:
        return {
            "action": "escalate",
            "reason": reason,
            "attempt": attempt_count,
            "ticket_id": ticket_id,
        }


def save_checkpoint(
    ticket_id: str,
    workspace: str,
    agent: str,
    progress: str,
    artifacts: Optional[list[str]] = None,
    next_step: str = "",
) -> Checkpoint:
    """Save a progress checkpoint for crash recovery."""
    checkpoint = Checkpoint(
        ticket_id=ticket_id,
        workspace=workspace,
        agent=agent,
        progress=progress,
        artifacts=artifacts or [],
        next_step=next_step,
    )

    activity_log(
        workspace=workspace,
        agent=agent,
        model="system",
        task=f"Checkpoint: {progress[:100]}",
        status="completed",
    )

    return checkpoint


class Watchdog:
    """Monitors agent health via heartbeats."""

    def __init__(self, heartbeat_timeout: int = 90):
        self.heartbeat_timeout = heartbeat_timeout
        self._agents: dict[str, HealthStatus] = {}

    def register_agent(self, agent: str):
        """Register an agent for health monitoring."""
        self._agents[agent] = HealthStatus(
            agent=agent,
            alive=True,
            last_heartbeat=time.time(),
        )

    def heartbeat(self, agent: str):
        """Record a heartbeat from an agent."""
        if agent in self._agents:
            self._agents[agent].last_heartbeat = time.time()
            self._agents[agent].alive = True
            self._agents[agent].consecutive_failures = 0
            self._agents[agent].status = "healthy"

    def check_health(self) -> list[HealthStatus]:
        """Check all agents for missed heartbeats. Returns unhealthy agents."""
        now = time.time()
        unhealthy = []

        for agent, status in self._agents.items():
            elapsed = now - status.last_heartbeat
            if elapsed > self.heartbeat_timeout:
                status.alive = False
                status.consecutive_failures += 1

                if status.consecutive_failures >= 3:
                    status.status = "dead"
                else:
                    status.status = "degraded"

                unhealthy.append(status)

        return unhealthy

    def get_status(self, agent: str) -> Optional[HealthStatus]:
        """Get health status for a specific agent."""
        return self._agents.get(agent)

    def all_status(self) -> dict[str, HealthStatus]:
        """Get health status for all registered agents."""
        return self._agents.copy()
