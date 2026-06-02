"""Linear GraphQL integration for CIPHER-OS.

Each workspace can have its own Linear API key stored in workspace config.
All calls use httpx (sync) — same dep already in use.
"""

import json
import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

GRAPHQL_URL = "https://api.linear.app/graphql"


def _query(api_key: str, query: str, variables: Optional[dict] = None) -> dict:
    """Execute a Linear GraphQL query/mutation. Raises on HTTP error."""
    payload: dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = httpx.post(
        GRAPHQL_URL,
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        msgs = "; ".join(e.get("message", str(e)) for e in data["errors"])
        raise ValueError(f"Linear API error: {msgs}")
    return data.get("data", {})


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def get_open_issues(api_key: str, limit: int = 30) -> list[dict]:
    """Return open issues (not completed/cancelled) for the viewer's teams."""
    q = """
    query($limit: Int!) {
      issues(
        first: $limit
        filter: { state: { type: { nin: ["completed", "canceled"] } } }
        orderBy: updatedAt
      ) {
        nodes {
          identifier title priority
          state { name type }
          assignee { name }
          team { key }
          url
        }
      }
    }
    """
    data = _query(api_key, q, {"limit": limit})
    return data.get("issues", {}).get("nodes", [])


def get_my_issues(api_key: str, limit: int = 30) -> list[dict]:
    """Return issues assigned to the viewer."""
    q = """
    query($limit: Int!) {
      viewer {
        assignedIssues(
          first: $limit
          filter: { state: { type: { nin: ["completed", "canceled"] } } }
          orderBy: updatedAt
        ) {
          nodes {
            identifier title priority
            state { name type }
            team { key }
            url
          }
        }
      }
    }
    """
    data = _query(api_key, q, {"limit": limit})
    return data.get("viewer", {}).get("assignedIssues", {}).get("nodes", [])


def search_issues(api_key: str, text: str, limit: int = 20) -> list[dict]:
    q = """
    query($q: String!, $limit: Int!) {
      issueSearch(query: $q, first: $limit) {
        nodes {
          identifier title priority
          state { name type }
          assignee { name }
          team { key }
          url
        }
      }
    }
    """
    data = _query(api_key, q, {"q": text, "limit": limit})
    return data.get("issueSearch", {}).get("nodes", [])


def get_teams(api_key: str) -> list[dict]:
    q = "{ teams { nodes { id name key } } }"
    data = _query(api_key, q)
    return data.get("teams", {}).get("nodes", [])


def get_workflow_states(api_key: str, team_key: str) -> list[dict]:
    q = """
    query($key: String!) {
      workflowStates(filter: { team: { key: { eq: $key } } }) {
        nodes { id name type }
      }
    }
    """
    data = _query(api_key, q, {"key": team_key})
    return data.get("workflowStates", {}).get("nodes", [])


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------

def create_issue(
    api_key: str,
    team_id: str,
    title: str,
    description: str = "",
    priority: int = 3,  # 0=none,1=urgent,2=high,3=medium,4=low
) -> dict:
    """Create a Linear issue and return {id, identifier, url}."""
    q = """
    mutation($input: IssueCreateInput!) {
      issueCreate(input: $input) {
        success
        issue { id identifier title url }
      }
    }
    """
    variables = {
        "input": {
            "teamId": team_id,
            "title": title,
            "description": description,
            "priority": priority,
        }
    }
    data = _query(api_key, q, variables)
    result = data.get("issueCreate", {})
    if not result.get("success"):
        raise ValueError("issueCreate returned success=false")
    return result.get("issue", {})


# ---------------------------------------------------------------------------
# Formatting helpers (for Cipher's context injection)
# ---------------------------------------------------------------------------

PRIORITY_LABEL = {0: "none", 1: "urgent", 2: "high", 3: "medium", 4: "low"}


def format_issues_for_context(issues: list[dict], workspace: str) -> str:
    """Format Linear issues into a compact text block for Cipher."""
    if not issues:
        return f"[TICKETS_RESULT: no open issues in workspace `{workspace}`]"

    lines = [f"[TICKETS_RESULT: {len(issues)} open issue(s) in `{workspace}` via Linear]"]
    for issue in issues:
        pri = PRIORITY_LABEL.get(issue.get("priority", 0), "?")
        state = issue.get("state", {}).get("name", "?")
        assignee = (issue.get("assignee") or {}).get("name", "unassigned")
        team = (issue.get("team") or {}).get("key", "?")
        url = issue.get("url", "")
        lines.append(
            f"- **{issue['identifier']}** [{state}] [{pri}] {issue['title']} "
            f"(team: {team}, assigned: {assignee}) {url}"
        )
    return "\n".join(lines)
