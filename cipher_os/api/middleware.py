"""Auth middleware — JWT token validation for all protected routes."""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .auth import verify_token

# Routes that do NOT require authentication
PUBLIC_PATHS = {
    "/api/v1/auth/status",
    "/api/v1/auth/setup",
    "/api/v1/auth/login",
    "/api/v1/health",
}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Always allow public API paths
        if path in PUBLIC_PATHS:
            return await call_next(request)

        # Always allow static assets and SPA routes
        if not path.startswith("/api/"):
            return await call_next(request)

        # Extract token — Bearer header OR ?token= query param (WebSocket)
        token = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

        # WebSocket connections pass token as query param
        if not token:
            token = request.query_params.get("token")

        if not token:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"},
            )

        username = verify_token(token)
        if not username:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"},
            )

        request.state.username = username
        return await call_next(request)
