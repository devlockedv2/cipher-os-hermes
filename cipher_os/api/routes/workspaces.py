"""Workspaces routes — manage workspaces and their skills."""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from ...core.workspace import (
    list_workspaces, create_workspace, delete_workspace,
    get_workspace_path, create_project,
)
from ...core.config import get_linear_api_key, set_linear_api_key
from ...activity.log import stats as activity_stats

router = APIRouter()


class WorkspaceCreate(BaseModel):
    name: str
    template: Optional[str] = None


class ProjectCreate(BaseModel):
    name: str


class LinearSettings(BaseModel):
    api_key: str


@router.get("")
async def list_all_workspaces():
    """List all workspaces."""
    workspaces = list_workspaces()
    result = []
    for ws in workspaces:
        stats = activity_stats(workspace=ws["name"])
        linear_configured = bool(get_linear_api_key(ws["name"]))
        result.append({
            **ws,
            "cost_total": stats.get("total_cost") or 0,
            "tokens_total": (stats.get("total_input_tokens") or 0) + (stats.get("total_output_tokens") or 0),
            "linear_configured": linear_configured,
        })
    return result


@router.get("/{name}")
async def get_workspace(name: str):
    """Get workspace details."""
    try:
        path = get_workspace_path(name)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Workspace '{name}' not found")

    stats = activity_stats(workspace=name)
    linear_configured = bool(get_linear_api_key(name))

    skills_dir = path / "skills"
    skills = []
    if skills_dir.exists():
        for s in skills_dir.iterdir():
            if s.is_dir() and (s / "SKILL.md").exists():
                skills.append({"name": s.name})

    return {
        "name": name,
        "path": str(path),
        "skills": skills,
        "stats": stats,
        "linear_configured": linear_configured,
    }


@router.put("/{name}/integrations/linear")
async def set_linear_key(name: str, body: LinearSettings):
    """Store a Linear API key for this workspace."""
    try:
        get_workspace_path(name)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Workspace '{name}' not found")
    set_linear_api_key(name, body.api_key.strip())
    return {"success": True, "workspace": name, "linear_configured": True}


@router.delete("/{name}/integrations/linear")
async def remove_linear_key(name: str):
    """Remove the Linear API key for this workspace."""
    set_linear_api_key(name, "")
    return {"success": True, "workspace": name, "linear_configured": False}


@router.post("")
async def create_new_workspace(body: WorkspaceCreate):
    """Create a new workspace."""
    try:
        path = create_workspace(body.name)
        return {"name": body.name, "path": str(path)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{name}")
async def remove_workspace(name: str, x_confirm: Optional[str] = Header(None)):
    """Delete a workspace. Requires X-Confirm: delete header."""
    if x_confirm != "delete":
        raise HTTPException(status_code=400, detail="Must include header X-Confirm: delete")
    try:
        delete_workspace(name, confirm=True)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{name}/projects")
async def create_new_project(name: str, body: ProjectCreate):
    """Create a project within a workspace."""
    try:
        path = create_project(name, body.name)
        return {"name": body.name, "path": str(path)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
