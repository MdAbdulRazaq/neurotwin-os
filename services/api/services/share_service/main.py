"""
SHARE SERVICE — Phase 12 Viral Loop
POST /api/share/create  → generates tokenised share link
GET  /api/share/{id}    → returns preview payload for /share/[id] page
DELETE /api/share/{id}  → removes a share token
"""
import os, uuid, logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("neurotwin.share")
router = APIRouter()

# INTEGRATION: replace with DB table ShareToken (id, user_id, preview_data, created_at)
_shares: dict = {}

class CreateShareRequest(BaseModel):
    user_id: str
    simulation_title: str
    preview_text: str
    preview_data: Optional[dict] = None

class SharePreview(BaseModel):
    id: str
    simulation_title: str
    preview_text: str
    preview_data: Optional[dict]
    share_url: str
    created_at: str

BASE_URL = os.environ.get("NEXT_PUBLIC_API_URL", "http://localhost")

@router.post("/api/share/create", response_model=SharePreview, status_code=201)
async def create_share(body: CreateShareRequest):
    share_id = str(uuid.uuid4())[:12]
    # INTEGRATION: INSERT INTO share_tokens (id, user_id, preview_data, created_at)
    _shares[share_id] = {
        "id": share_id, "user_id": body.user_id,
        "simulation_title": body.simulation_title,
        "preview_text": body.preview_text,
        "preview_data": body.preview_data or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    share_url = f"{BASE_URL}/share/{share_id}"
    logger.info("Share created: %s for user %s", share_id, body.user_id)
    return {**_shares[share_id], "share_url": share_url}

@router.get("/api/share/{share_id}")
async def get_share_preview(share_id: str):
    share = _shares.get(share_id)
    # INTEGRATION: SELECT * FROM share_tokens WHERE id=share_id
    if not share:
        raise HTTPException(status_code=404, detail="Share not found or expired")
    return {**share, "share_url": f"{BASE_URL}/share/{share_id}"}

@router.delete("/api/share/{share_id}", status_code=204)
async def delete_share(share_id: str):
    # INTEGRATION: DELETE FROM share_tokens WHERE id=share_id
    _shares.pop(share_id, None)
