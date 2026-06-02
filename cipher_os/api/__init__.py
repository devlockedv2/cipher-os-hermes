"""FastAPI backend for CIPHER-OS Command Center."""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .routes import dashboard, agents, tickets, workspaces, activity, settings, chat
from .websocket.manager import ConnectionManager

app = FastAPI(
    title="CIPHER-OS Command Center",
    version="0.1.0",
    description="Multi-agent orchestration dashboard",
)

# CORS for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(dashboard.router, prefix="/api/v1", tags=["dashboard"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(tickets.router, prefix="/api/v1/tickets", tags=["tickets"])
app.include_router(workspaces.router, prefix="/api/v1/workspaces", tags=["workspaces"])
app.include_router(activity.router, prefix="/api/v1/activity", tags=["activity"])
app.include_router(settings.router, prefix="/api/v1/settings", tags=["settings"])
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
