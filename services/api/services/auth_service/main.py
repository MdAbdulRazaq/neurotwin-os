"""
AUTH SERVICE — Phase 12/13 Continuation
JWT signup/login using bcrypt directly (NEVER passlib per critical rule).
Grants free simulations on signup + referral bonus.
Endpoints: /api/auth/signup  /api/auth/login  /api/auth/me  /api/auth/logout
"""
import os, uuid, logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt as _bcrypt
from jose import jwt, JWTError
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

logger = logging.getLogger("neurotwin.auth")
router = APIRouter()

SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
ALGORITHM  = "HS256"
TOKEN_EXP_HOURS = 24 * 30   # 30 days
REFERRAL_BONUS  = int(os.environ.get("REFERRAL_BONUS_SIMULATIONS", "10"))
REFERRER_BONUS  = int(os.environ.get("REFERRER_BONUS_SIMULATIONS", "5"))
FREE_SIMULATIONS_ON_SIGNUP = 5

security = HTTPBearer(auto_error=False)

# ── In-memory store (replace with DB INTEGRATION: comment blocks below) ────────
_users: dict = {}   # INTEGRATION: replace with DB lookup in signup() and login()
_usage: dict = {}   # INTEGRATION: replace with Redis INCR in grant_simulations()

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    referral_id: Optional[str] = None
    plan_intent: Optional[str] = "free"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    plan: str

def create_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id, "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXP_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def hash_password(plain: str) -> str:
    salt = _bcrypt.gensalt()
    return _bcrypt.hashpw(plain.encode(), salt).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode(), hashed.encode())

def grant_simulations(user_id: str, count: int):
    # INTEGRATION: Redis INCR usage:{user_id}:sims:{month}
    _usage.setdefault(user_id, 0)
    _usage[user_id] += count

async def get_current_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if not creds:
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    return verify_token(creds.credentials)

@router.post("/api/auth/signup", response_model=TokenResponse, status_code=201)
async def signup(body: SignupRequest):
    if body.email in _users:
        raise HTTPException(status_code=409, detail="Email already registered")
    user_id = str(uuid.uuid4())
    hashed  = hash_password(body.password)
    # INTEGRATION: INSERT INTO users (id, email, password_hash, plan) VALUES (...)
    _users[body.email] = {"id": user_id, "email": body.email, "hash": hashed, "plan": "free"}
    grant_simulations(user_id, FREE_SIMULATIONS_ON_SIGNUP)
    if body.referral_id:
        grant_simulations(user_id, REFERRAL_BONUS)
        # INTEGRATION: apply_referral(body.referral_id, referrer_bonus=REFERRER_BONUS)
    token = create_token(user_id, body.email)
    logger.info("Signup: %s plan_intent=%s", body.email, body.plan_intent)
    return TokenResponse(access_token=token, user_id=user_id, email=body.email, plan="free")

@router.post("/api/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    user = _users.get(body.email)
    # INTEGRATION: SELECT * FROM users WHERE email=body.email
    if not user or not verify_password(body.password, user["hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(user["id"], body.email)
    return TokenResponse(access_token=token, user_id=user["id"], email=body.email, plan=user.get("plan","free"))

@router.get("/api/auth/me")
async def me(current_user: dict = Depends(get_current_user)):
    return {"user_id": current_user["sub"], "email": current_user["email"]}

@router.post("/api/auth/logout", status_code=204)
async def logout():
    return  # Client-side token removal; stateless JWT
