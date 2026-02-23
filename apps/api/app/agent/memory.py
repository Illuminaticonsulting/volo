"""
VOLO — Memory Manager
Handles storing, retrieving, and searching the agent's memory.
Memories persist across conversations — the agent never forgets.
"""

from typing import Optional
from datetime import datetime


class MemoryManager:
    """
    Manages the agent's long-term memory.
    Uses in-memory store for now, PostgreSQL + pgvector in production.
    """

    def __init__(self):
        # In-memory store for development
        self._memories: list[dict] = []

    async def store(
        self,
        user_id: str = "default",
        category: str = "fact",
        content: str = "",
        source: str = "conversation",
        confidence: float = 1.0,
    ) -> dict:
        """Store a new memory."""
        memory = {
            "id": f"mem_{len(self._memories) + 1}",
            "user_id": user_id,
            "category": category,
            "content": content,
            "source": source,
            "confidence": confidence,
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed_at": datetime.utcnow().isoformat(),
        }
        self._memories.append(memory)
        return memory

    async def search(
        self,
        query: str,
        user_id: str = "default",
        category: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict]:
        """
        Search memories by keyword match.
        In production, this uses pgvector for semantic search.
        """
        results = []
        query_lower = query.lower()

        for memory in self._memories:
            if memory["user_id"] != user_id:
                continue
            if category and memory["category"] != category:
                continue
            if query_lower in memory["content"].lower():
                memory["last_accessed_at"] = datetime.utcnow().isoformat()
                results.append(memory)

        return results[:limit]

    async def get_all(
        self,
        user_id: str = "default",
        category: Optional[str] = None,
    ) -> list[dict]:
        """Get all memories for a user."""
        results = [
            m for m in self._memories
            if m["user_id"] == user_id
            and (category is None or m["category"] == category)
        ]
        return results

    async def delete(self, memory_id: str) -> bool:
        """Delete a specific memory."""
        self._memories = [m for m in self._memories if m["id"] != memory_id]
        return True

    async def clear_all(self, user_id: str = "default") -> int:
        """Clear all memories for a user. Returns count deleted."""
        before = len(self._memories)
        self._memories = [m for m in self._memories if m["user_id"] != user_id]
        return before - len(self._memories)
