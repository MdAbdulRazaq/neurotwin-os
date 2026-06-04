"""
NEUROTWIN OS — Auth Router
JWT-based authentication: register, login, refresh, logout, device management.
"""

import hashlib
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError, jwt
import bcrypt as _bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserProfile,
    UserPreferences,
)
from app.models.user import User

router = APIRouter()
logger = logging.getLogger("neurotwin.auth")

def _hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt(rounds=12)).decode()

def _verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode(), hashed.encode())

# ── JWT helpers ───────────────────────────────────────────────────────────────

def _create_access_token(user_id: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY.get_secret_value(), algorithm=settings.JWT_ALGORITHM)


def _create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
        "jti": os.urandom(16).hex(),  # unique token ID for revocation
    }
    return jwt.encode(payload, settings.SECRET_KEY.get_secret_value(), algorithm=settings.JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


# ── Register ──────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check email uniqueness
    result = await db.execute(select(User).where(User.email == req.email.lower()))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    hashed_pw = _hash_password(req.password)
    user = User(
        email=req.email.lower(),
        name=req.name,
        hashed_password=hashed_pw,
        locale=req.locale,
        preferences={},
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    user_id = str(user.id)
    logger.info(f"New user registered: id={user_id} email={user.email}")

    return TokenResponse(
        access_token=_create_access_token(user_id, user.email),
        refresh_token=_create_refresh_token(user_id),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email.lower()))
    user = result.scalar_one_or_none()

    if not user or not _verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user_id = str(user.id)

    # Track device if provided
    if req.device_id:
        redis = request.app.state.redis
        device_key = f"device:{user_id}:{req.device_id}"
        await redis.setex(
            device_key,
            settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
            req.device_id,
        )

    logger.info(f"User login: id={user_id}")
    return TokenResponse(
        access_token=_create_access_token(user_id, user.email),
        refresh_token=_create_refresh_token(user_id),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ── Refresh ───────────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = _decode_token(req.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token type mismatch")

    user_id = payload["sub"]
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return TokenResponse(
        access_token=_create_access_token(user_id, user.email),
        refresh_token=_create_refresh_token(user_id),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/logout", status_code=204)
async def logout(request: Request, db: AsyncSession = Depends(get_db)):
    # In production: revoke refresh token JTI in Redis blocklist
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if token:
        try:
            payload = _decode_token(token)
            redis = request.app.state.redis
            exp = payload.get("exp", 0)
            ttl = max(0, int(exp - datetime.now(timezone.utc).timestamp()))
            jti = payload.get("jti", token[:16])
            await redis.setex(f"revoked:{jti}", ttl, "1")
        except Exception:
            pass  # swallow errors on logout
    return


# ── GDPR: Delete account ──────────────────────────────────────────────────────

@router.delete("/account", status_code=204)
async def delete_account(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Right to erasure — deletes user and all associated data."""
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    payload = _decode_token(token)
    user_id = payload["sub"]

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Trigger memory wipe
    memory_mgr = getattr(request.app.state, "memory_manager", None)
    if memory_mgr:
        await memory_mgr.forget_user(user_id)

    await db.delete(user)
    await db.commit()
    logger.info(f"Account deleted (GDPR): user_id={user_id}")
    return
