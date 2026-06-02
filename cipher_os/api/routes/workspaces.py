"""Workspaces routes — manage workspaces and their skills."""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from ...core.workspace import (
    list_workspaces, create_workspace, delete_workspace,
    get_workspace_path, create_project,
)
from ...activity.log import stats as activity_stats

router = APIRouter()


class WorkspaceCreate(BaseModel):
    name: str
    template: Optional[str] = None


class ProjectCreate(BaseModel):
    name: str


@router.get("")
async def list_all_workspaces():
    """List all workspaces."""
    workspaces = list_workspaces()
    result = []
    for ws in workspaces:
        stats = activity_stats(workspace=ws["name"])
        result.append({
            **ws,
            "cost_total": stats.get("total_cost") or 0,
            "tokens_total": (stats.get("total_input_tokens") or 0) + (stats.get("total_output_tokens") or 0),
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

    # List skills
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
    }


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
