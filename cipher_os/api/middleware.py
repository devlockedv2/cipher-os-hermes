"""Auth middleware — JWT token validation for all protected routes."""

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from .auth import verify_token, is_setup


# Paths that don't require authentication
PUBLIC_PATHS = {
    "/api/v1/health",
    "/api/v1/auth/login",
    "/api/v1/auth/setup",
    "/api/v1/auth/status",
    "/docs",
    "/openapi.json",
    "/redoc",
}

# Prefixes that are always public (static assets, SPA)
PUBLIC_PREFIXES = ("/assets/", "/favicon")


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Require valid JWT for all API routes (except login/setup/health)."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Public paths — no auth needed
        if path in PUBLIC_PATHS:
            return await call_next(request)

        # Public prefixes (static assets)
        if any(path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)

        # Non-API paths (SPA frontend) — serve without auth
        # The frontend handles login redirect client-side
        if not path.startswith("/api/"):
            return await call_next(request)

        # WebSocket — auth handled at connection level
        if path == "/ws":
            return await call_next(request)

        # All other API routes require JWT
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

        token = auth_header.removeprefix("Bearer ")
        username = verify_token(token)

        if not username:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        # Attach user to request state
        request.state.user = username
        return await call_next(request)
