"""FastAPI backend for CIPHER-OS Command Center."""

from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .middleware import AuthMiddleware as JWTAuthMiddleware
from .routes import dashboard, agents, tickets, workspaces, activity, settings, chat, plan
from .routes import auth as auth_routes
from .websocket import ConnectionManager

app = FastAPI(
    title="CIPHER-OS Command Center",
    version="0.1.0",
    description="Multi-agent orchestration dashboard",
)

# JWT auth middleware
app.add_middleware(JWTAuthMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins since we use JWT auth
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(auth_routes.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(dashboard.router, prefix="/api/v1", tags=["dashboard"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(tickets.router, prefix="/api/v1/tickets", tags=["tickets"])
app.include_router(workspaces.router, prefix="/api/v1/workspaces", tags=["workspaces"])
app.include_router(activity.router, prefix="/api/v1/activity", tags=["activity"])
app.include_router(settings.router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(plan.router, prefix="/api/v1", tags=["plan"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])

# WebSocket manager
ws_manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await ws_manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.get("/api/v1/health")
async def health():
    return {
        "status": "ok",
        "version": "0.1.0",
    }


# Serve React frontend (SPA) — must be LAST (catch-all)
DIST_DIR = Path(__file__).parent.parent.parent / "web" / "dist"

if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_root():
        return FileResponse(str(DIST_DIR / "index.html"))

    @app.api_route("/{full_path:path}", methods=["GET"], include_in_schema=False)
    async def serve_spa(full_path: str):
        """Serve React SPA — all non-API routes return index.html."""
        if full_path.startswith("api/"):
            raise StarletteHTTPException(status_code=404)
        file_path = DIST_DIR / full_path
        if full_path and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(DIST_DIR / "index.html"))
