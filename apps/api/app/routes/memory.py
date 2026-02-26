"""
VOLO — Memory Route
Endpoints for viewing and managing agent memory.
Backed by PostgreSQL — memories survive restarts.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional

from app.agent.memory import MemoryManager
from app.auth import get_current_user, CurrentUser

router = APIRouter()
memory_manager = MemoryManager()


class MemoryCreate(BaseModel):
    category: str
    content: str
    source: Optional[str] = "manual"


@router.get("/memory")
async def list_memories(
    category: Optional[str] = None,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List memories the agent has about the user (paginated)."""
    memories = await memory_manager.get_all(
        user_id=current_user.user_id,
        category=category,
        limit=limit,
        offset=offset,
    )
    return {
        "memories": memories,
        "limit": limit,
        "offset": offset,
    }


@router.post("/memory")
async def create_memory(memory: MemoryCreate, current_user: CurrentUser = Depends(get_current_user)):
    """Manually add a memory."""
    result = await memory_manager.store(
        user_id=current_user.user_id,
        category=memory.category,
        content=memory.content,
        source=memory.source or "manual",
    )
    return {"success": True, "memory": result}


@router.delete("/memory/{memory_id}")
async def delete_memory(memory_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """Delete a specific memory (selective amnesia)."""
    deleted = await memory_manager.delete(memory_id)
    if not deleted:
        return {"success": False, "message": "Memory not found."}
    return {
        "success": True,
        "message": f"Memory {memory_id} deleted. Forgotten permanently.",
    }


@router.delete("/memory")
async def clear_all_memories(current_user: CurrentUser = Depends(get_current_user)):
    """Clear ALL memories. Nuclear option."""
    count = await memory_manager.clear_all(user_id=current_user.user_id)
    return {
        "success": True,
        "cleared": count,
        "message": f"All {count} memories cleared. Starting fresh.",
    }


@router.get("/memory/search")
async def search_memories(q: str, category: Optional[str] = None, limit: int = 10, current_user: CurrentUser = Depends(get_current_user)):
    """Search memories by keyword."""
    results = await memory_manager.search(
        query=q, user_id=current_user.user_id, category=category, limit=limit
    )
    return {"results": results, "total": len(results), "query": q}


@router.get("/memory/export")
async def export_memories(
    limit: int = Query(10_000, ge=1, le=50_000),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Export memories as JSON (up to 50 000 records). Data portability."""
    memories = await memory_manager.get_all(user_id=current_user.user_id, limit=limit)
    return {
        "memories": memories,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "format": "volo-memory-v1",
        "total": len(memories),
    }
