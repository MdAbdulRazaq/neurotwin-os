"""NEUROTWIN OS — Memory Router"""
import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Memory as DBMemory, get_db
from app.core.schemas import MemoryDeleteRequest, MemoryListResponse, MemoryEntry
from app.core.config import settings
from app.middleware.auth import get_current_user

router = APIRouter()
logger = logging.getLogger("neurotwin.memory")


@router.get("", response_model=MemoryListResponse)
async def list_memories(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    offset: int = 0,
    limit: int = 20,
):
    """List user's long-term memories with pagination."""
    user_id = current_user["id"]
    # Total count
    total_q = select(func.count()).select_from(DBMemory).where(DBMemory.user_id == user_id)
    total = (await db.execute(total_q)).scalar_one()

    # Fetch memories
    stmt = (
        select(DBMemory)
        .where(DBMemory.user_id == user_id)
        .order_by(DBMemory.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    memories = result.scalars().all()

    entries = []
    for m in memories:
        entries.append(
            MemoryEntry(
                id=str(m.id),
                type=m.type,
                summary=m.summary,
                timestamp=m.created_at,
                importance=m.importance,
                emotion=m.emotion,
            )
        )

    return MemoryListResponse(memories=entries, total=total, has_more=offset + len(entries) < total)


@router.delete("")
async def delete_memories(
    req: MemoryDeleteRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete specific memories by ID."""
    user_id = current_user["id"]
    memory_ids = req.memory_ids

    # Convert to UUIDs
    try:
        memory_uuids = [uuid.UUID(x) for x in memory_ids]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid memory ID format")

    # Fetch memory records to get pinecone_vector_id
    stmt = select(DBMemory).where(
        DBMemory.user_id == user_id,
        DBMemory.id.in_(memory_uuids)
    )
    result = await db.execute(stmt)
    db_memories = result.scalars().all()

    if not db_memories:
        return {"deleted": 0}

    pinecone_ids = [m.pinecone_vector_id for m in db_memories if m.pinecone_vector_id]

    # Delete from Pinecone if configured
    memory_mgr = getattr(request.app.state, "memory_manager", None)
    if memory_mgr and pinecone_ids and settings.PINECONE_API_KEY:
        try:
            await memory_mgr.pinecone.delete_vectors(user_id, pinecone_ids)
        except Exception as e:
            logger.warning(f"Pinecone deletion failed: {e}")

    # Delete from DB
    delete_stmt = delete(DBMemory).where(DBMemory.id.in_([m.id for m in db_memories]))
    await db.execute(delete_stmt)
    await db.commit()

    return {"deleted": len(db_memories)}


@router.delete("/all")
async def forget_all(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete all memories for the current user (GDPR)."""
    user_id = current_user["id"]
    memory_mgr = getattr(request.app.state, "memory_manager", None)
    if memory_mgr:
        await memory_mgr.forget_user(user_id)
    # Delete all memories from PostgreSQL
    delete_stmt = delete(DBMemory).where(DBMemory.user_id == user_id)
    await db.execute(delete_stmt)
    await db.commit()
    return {"status": "all_memories_deleted", "user_id": user_id}
