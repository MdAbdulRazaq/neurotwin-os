"""NEUROTWIN OS — User Router"""
import logging
from fastapi import APIRouter, Depends, Request
from app.core.schemas import UserProfile, UserPreferences, UpdatePreferencesRequest
from app.middleware.auth import get_current_user

router = APIRouter()
logger = logging.getLogger("neurotwin.user")


@router.get("/me")
async def get_profile(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "name": current_user.get("name", "User"),
        "locale": "en",
        "preferences": current_user.get("preferences", {}),
    }


@router.patch("/preferences")
async def update_preferences(
    req: UpdatePreferencesRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]
    # In production: persist to DB
    logger.info(f"Updated preferences for user={user_id}")
    return {"status": "ok", "preferences": req.preferences}
