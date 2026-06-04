"""
NEUROTWIN OS — JWT Auth Middleware
Validates Bearer tokens on every protected request.
"""

import logging
from typing import List, Optional

from fastapi import HTTPException, Request
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger("neurotwin.middleware.auth")


class JWTMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, exclude_paths: Optional[List[str]] = None):
        super().__init__(app)
        self.exclude_paths = set(exclude_paths or [])

    async def dispatch(self, request: Request, call_next):
        if any(request.url.path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)

        # Skip WebSocket upgrade
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"error": "Missing or invalid Authorization header"})

        token = auth_header.removeprefix("Bearer ").strip()
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY.get_secret_value(),
                algorithms=[settings.JWT_ALGORITHM],
            )
            if payload.get("type") != "access":
                return JSONResponse(status_code=401, content={"error": "Invalid token type"})

            # Check revocation list
            jti = payload.get("jti", token[:16])
            redis = getattr(request.app.state, "redis", None)
            if redis:
                is_revoked = await redis.get(f"revoked:{jti}")
                if is_revoked:
                    return JSONResponse(status_code=401, content={"error": "Token revoked"})

            request.state.user_id = payload["sub"]
            request.state.user_email = payload.get("email", "")
            request.state.token_payload = payload
        except JWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            return JSONResponse(status_code=401, content={"error": f"Token invalid: {e}"})

        return await call_next(request)


async def get_current_user(request: Request) -> dict:
    """Dependency: extract current user from request state."""
    if not hasattr(request.state, "user_id"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {
        "id": request.state.user_id,
        "email": request.state.user_email,
        "name": request.state.token_payload.get("name", "User"),
        "preferences": request.state.token_payload.get("prefs", {}),
    }
