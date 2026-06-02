"""WebSocket connection manager."""

import json
from typing import Set
from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections and channel subscriptions."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.subscriptions: dict[WebSocket, set[str]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        self.subscriptions[websocket] = set()

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        self.subscriptions.pop(websocket, None)

    async def handle_message(self, websocket: WebSocket, data: dict):
        """Handle incoming WebSocket messages."""
        msg_type = data.get("type")

        if msg_type == "subscribe":
            channels = data.get("channels", [])
            self.subscriptions[websocket].update(channels)

        elif msg_type == "unsubscribe":
            channels = data.get("channels", [])
            self.subscriptions[websocket] -= set(channels)

        elif msg_type == "chat_message":
            # Forward to chat handler
            await self.broadcast("chat", {
                "type": "chat_received",
                "message": data.get("message", ""),
                "workspace": data.get("workspace", ""),
            })

    async def broadcast(self, channel: str, message: dict):
        """Broadcast a message to all subscribers of a channel."""
        disconnected = []
        for ws in self.active_connections:
            if channel in self.subscriptions.get(ws, set()):
                try:
                    await ws.send_json(message)
                except Exception:
                    disconnected.append(ws)

        for ws in disconnected:
            self.disconnect(ws)

    async def broadcast_all(self, message: dict):
        """Broadcast to all connected clients regardless of subscription."""
        disconnected = []
        for ws in self.active_connections:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect(ws)
