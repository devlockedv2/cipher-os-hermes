"""Orchestrator (Cipher) — routing logic, delegation, approval flow."""

import json
from dataclasses import dataclass
from typing import Optional

from ..tickets import create_ticket, update_ticket, query_tickets
from ..activity.log import log as activity_log


# Type → default agent mapping
TYPE_ROUTING = {
    "research": "lens",
    "planning": "atlas",
    "development": "forge",
    "devops": "sentinel",
    "bug": "forge",
    "question": "lens",
}

# Intent keywords → task type
INTENT_KEYWORDS = {
    "research": ["find out", "compare", "what is", "look up", "investigate", "analyze", "evaluate", "research", "learn about"],
    "planning": ["plan", "design", "architect", "scope", "estimate", "break down", "decompose", "structure", "outline"],
    "development": ["build", "fix", "implement", "refactor", "test", "code", "write", "debug", "create", "add", "update", "modify"],
    "devops": ["deploy", "provision", "monitor", "CI", "infra", "server", "pipeline", "docker", "kubernetes", "staging", "prod"],
}

# Actions that ALWAYS escalate to user (Cipher cannot approve)
DESTRUCTIVE_ACTIONS = [
    "deploy to prod",
    "delete database",
    "terraform destroy",
    "drop table",
    "rm -rf",
    "force push to main",
    "revoke access",
    "delete workspace",
    "purge data",
]


@dataclass
class DelegationBrief:
    """Structured brief passed to a sub-agent."""
    ticket_id: str
    agent: str
    workspace: str
    project: Optional[str]
    context: str
    inputs: list[str]
    constraints: list[str]
    success_criteria: str


@dataclass
class RoutingDecision:
    """Result of the routing logic."""
    agent: str
    task_type: str
    confidence: float  # 0.0 - 1.0
    reason: str
    needs_decomposition: bool = False
    is_destructive: bool = False
    requires_user_approval: bool = False


def classify_intent(task_description: str) -> tuple[str, float]:
    """Classify task intent from description. Returns (type, confidence)."""
    description_lower = task_description.lower()

    scores: dict[str, int] = {}
    for task_type, keywords in INTENT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in description_lower)
        if score > 0:
            scores[task_type] = score

    if not scores:
        return "question", 0.3  # Low confidence default

    best_type = max(scores, key=lambda k: scores[k])
    # Confidence based on how many keywords matched vs total
    confidence = min(scores[best_type] / 3.0, 1.0)
    return best_type, confidence


def is_destructive(task_description: str) -> bool:
    """Check if a task involves destructive/irreversible actions."""
    description_lower = task_description.lower()
    return any(action in description_lower for action in DESTRUCTIVE_ACTIONS)


def route_task(
    task_description: str,
    workspace: str,
    project: Optional[str] = None,
    explicit_agent: Optional[str] = None,
    explicit_type: Optional[str] = None,
) -> RoutingDecision:
    """Route a task to the appropriate agent.

    Priority:
    1. Explicit agent override (user says "have Lens do this")
    2. Explicit type (from ticket or user)
    3. Intent classification from description
    """
    # Check for destructive actions
    destructive = is_destructive(task_description)

    # Priority 1: Explicit agent
    if explicit_agent:
        task_type = explicit_type or "development"
        return RoutingDecision(
            agent=explicit_agent,
            task_type=task_type,
            confidence=1.0,
            reason=f"Explicitly assigned to {explicit_agent}",
            is_destructive=destructive,
            requires_user_approval=destructive,
        )

    # Priority 2: Explicit type
    if explicit_type and explicit_type in TYPE_ROUTING:
        agent = TYPE_ROUTING[explicit_type]
        return RoutingDecision(
            agent=agent,
            task_type=explicit_type,
            confidence=0.9,
            reason=f"Routed by type '{explicit_type}' → {agent}",
            is_destructive=destructive,
            requires_user_approval=destructive,
        )

    # Priority 3: Intent classification
    task_type, confidence = classify_intent(task_description)
    agent = TYPE_ROUTING.get(task_type, "lens")

    # Check if task is compound (multiple domains)
    all_types = [t for t, kws in INTENT_KEYWORDS.items()
                 if any(kw in task_description.lower() for kw in kws)]
    needs_decomposition = len(all_types) > 1

    return RoutingDecision(
        agent=agent,
        task_type=task_type,
        confidence=confidence,
        reason=f"Intent classified as '{task_type}' → {agent} (confidence: {confidence:.1f})",
        needs_decomposition=needs_decomposition,
        is_destructive=destructive,
        requires_user_approval=destructive,
    )


def create_delegation_brief(
    ticket_id: str,
    agent: str,
    workspace: str,
    task_description: str,
    project: Optional[str] = None,
    inputs: Optional[list[str]] = None,
    constraints: Optional[list[str]] = None,
    success_criteria: str = "Task completed successfully",
) -> DelegationBrief:
    """Create a structured delegation brief for a sub-agent."""
    return DelegationBrief(
        ticket_id=ticket_id,
        agent=agent,
        workspace=workspace,
        project=project,
        context=task_description,
        inputs=inputs or [],
        constraints=constraints or [],
        success_criteria=success_criteria,
    )


def decompose_task(
    task_description: str,
    workspace: str,
    project: Optional[str] = None,
    created_by: str = "cipher",
) -> list[dict]:
    """Decompose a compound task into a ticket chain with dependencies.

    Returns list of created tickets in execution order.
    """
    # Determine which agents are needed
    all_types = []
    for task_type, keywords in INTENT_KEYWORDS.items():
        if any(kw in task_description.lower() for kw in keywords):
            all_types.append(task_type)

    if not all_types:
        all_types = ["development"]

    # Standard pipeline order
    pipeline_order = ["research", "planning", "development", "devops"]
    ordered_types = [t for t in pipeline_order if t in all_types]

    if not ordered_types:
        ordered_types = all_types[:1]

    tickets = []
    prev_ticket_id = None

    for task_type in ordered_types:
        agent = TYPE_ROUTING[task_type]
        depends = [prev_ticket_id] if prev_ticket_id else None

        ticket = create_ticket(
            workspace=workspace,
            title=f"[{task_type.upper()}] {task_description[:80]}",
            type=task_type,
            created_by=created_by,
            project=project,
            description=f"Part of compound task: {task_description}",
            assigned_to=agent,
            depends_on=depends,
            estimate="md",
        )
        tickets.append(ticket)
        prev_ticket_id = ticket["id"]

    return tickets


def approve_plan(
    task_description: str,
    routing: RoutingDecision,
    mode: str = "supervised",
) -> dict:
    """Determine if a plan can be auto-approved or needs escalation.

    Returns: {approved: bool, reason: str, escalate_to: 'user' | None}
    """
    # Destructive = always user
    if routing.is_destructive:
        return {
            "approved": False,
            "reason": "Destructive/irreversible action detected",
            "escalate_to": "user",
        }

    # Autonomous mode = approve everything non-destructive
    if mode == "autonomous":
        return {
            "approved": True,
            "reason": "Autonomous mode — auto-approved",
            "escalate_to": None,
        }

    # Supervised mode — Cipher approves routine, escalates complex
    if routing.confidence >= 0.3 and not routing.needs_decomposition:
        return {
            "approved": True,
            "reason": f"Routine task, high confidence routing to {routing.agent}",
            "escalate_to": None,
        }

    # Low confidence — escalate to user
    if routing.confidence < 0.2:
        return {
            "approved": False,
            "reason": f"Low confidence ({routing.confidence:.1f}) — needs clarification",
            "escalate_to": "user",
        }

    # Medium confidence, compound task — Cipher can approve
    return {
        "approved": True,
        "reason": f"Compound task — Cipher auto-approved decomposition to {routing.agent}",
        "escalate_to": None,
    }
