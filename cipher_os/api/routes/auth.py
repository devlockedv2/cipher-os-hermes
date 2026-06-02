"""Auth routes — login, setup, password change."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..auth import (
    is_setup, setup_credentials, verify_credentials,
    create_token, change_password,
)

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class SetupRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.get("/status")
async def auth_status():
    """Check if initial setup has been completed."""
    return {"setup_complete": is_setup()}


@router.post("/setup")
async def initial_setup(body: SetupRequest):
    """Create initial admin credentials (first run only)."""
    if is_setup():
        raise HTTPException(status_code=400, detail="Already configured. Use login.")

    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    setup_credentials(body.username, body.password)
    token = create_token(body.username)

    return {
        "success": True,
        "token": token,
        "message": "Credentials created. You are now logged in.",
    }


@router.post("/login")
async def login(body: LoginRequest):
    """Authenticate and receive a JWT token."""
    if not is_setup():
        raise HTTPException(status_code=400, detail="No credentials configured. Use /setup first.")

    if not verify_credentials(body.username, body.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_token(body.username)

    return {
        "success": True,
        "token": token,
        "username": body.username,
    }


@router.post("/change-password")
async def update_password(body: ChangePasswordRequest):
    """Change password (requires current password)."""
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

    try:
        change_password(body.current_password, body.new_password)
        return {"success": True, "message": "Password updated."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
