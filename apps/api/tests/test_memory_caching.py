"""
Tests for MemoryManager:
- search() caching: cache hit skips DB; cache miss populates cache
- get_all() pagination: limit/offset work correctly via the API
"""
import json

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from app.agent.memory import MemoryManager


# ── search() caching ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_cache_hit_skips_db():
    """A cache hit must return the cached rows without opening a DB session."""
    manager = MemoryManager()
    sentinel = [
        {
            "id": "m-sentinel", "user_id": "dev-user", "category": "fact",
            "content": "cached content", "source": "test", "confidence": 1.0,
            "created_at": None, "last_accessed_at": None,
        }
    ]

    with patch("app.agent.memory.cache") as mock_cache:
        mock_cache.get = AsyncMock(return_value=json.dumps(sentinel))

        with patch("app.agent.memory.async_session") as mock_db:
            result = await manager.search("cached content", user_id="dev-user")

        # DB must never be touched on a cache hit
        mock_db.assert_not_called()

    assert result == sentinel


@pytest.mark.asyncio
async def test_search_cache_miss_queries_db_and_stores():
    """On a cache miss, the result is fetched from DB and written to cache."""
    manager = MemoryManager()

    with patch("app.agent.memory.cache") as mock_cache:
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()

        result = await manager.search("nonexistent_zyx987", user_id="dev-user")

        # cache.set must be called exactly once
        mock_cache.set.assert_awaited_once()
        call_args = mock_cache.set.call_args
        key_arg = call_args[0][0]
        payload_arg = call_args[0][1]
        ttl_arg = call_args[1].get("ttl") if call_args[1] else call_args[0][2]

        assert key_arg.startswith("memsearch:dev-user:")
        assert json.loads(payload_arg) == result
        assert ttl_arg == 60


@pytest.mark.asyncio
async def test_search_cache_key_is_scoped_to_user_and_query():
    """Different users and queries must produce distinct cache keys."""
    manager = MemoryManager()
    captured_keys = []

    async def fake_set(key, value, *, ttl):
        captured_keys.append(key)

    with patch("app.agent.memory.cache") as mock_cache:
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock(side_effect=fake_set)

        await manager.search("alpha query", user_id="user-1")
        await manager.search("beta query", user_id="user-1")
        await manager.search("alpha query", user_id="user-2")

    assert len(set(captured_keys)) == 3, "Each user+query combination must use a unique cache key"
    assert all("user-1" in k or "user-2" in k for k in captured_keys)


@pytest.mark.asyncio
async def test_search_cache_key_includes_category():
    """The category filter must be part of the cache key."""
    manager = MemoryManager()
    captured_keys = []

    async def fake_set(key, value, *, ttl):
        captured_keys.append(key)

    with patch("app.agent.memory.cache") as mock_cache:
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock(side_effect=fake_set)

        await manager.search("test", user_id="dev-user", category="fact")
        await manager.search("test", user_id="dev-user", category="goal")

    assert len(set(captured_keys)) == 2
    assert any("fact" in k for k in captured_keys)
    assert any("goal" in k for k in captured_keys)


@pytest.mark.asyncio
async def test_search_bad_cache_json_falls_through_to_db():
    """Corrupt cache JSON must be ignored and the DB must be queried instead."""
    manager = MemoryManager()

    with patch("app.agent.memory.cache") as mock_cache:
        mock_cache.get = AsyncMock(return_value="NOT VALID JSON {{{")
        mock_cache.set = AsyncMock()

        # Should not raise; should fall back to DB
        result = await manager.search("anything", user_id="dev-user")
        assert isinstance(result, list)


# ── get_all() pagination via HTTP ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_memory_list_limit_respected(auth_client: AsyncClient):
    """GET /memory?limit=2 returns at most 2 memories."""
    # Ensure at least 3 memories exist
    for i in range(3):
        await auth_client.post(
            "/api/memory",
            json={"category": "fact", "content": f"pagination item {i}", "source": "test"},
        )

    resp = await auth_client.get("/api/memory?limit=2&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["memories"]) <= 2
    assert data["limit"] == 2
    assert data["offset"] == 0


@pytest.mark.asyncio
async def test_memory_list_offset_returns_different_items(auth_client: AsyncClient):
    """offset=0 and offset=1 must not return the same first element."""
    # Create 3 memories so offset makes sense
    for i in range(3):
        await auth_client.post(
            "/api/memory",
            json={"category": "fact", "content": f"offset test item {i}", "source": "test"},
        )

    r0 = await auth_client.get("/api/memory?limit=100&offset=0")
    r1 = await auth_client.get("/api/memory?limit=100&offset=1")
    assert r0.status_code == r1.status_code == 200

    ids_at_0 = [m["id"] for m in r0.json()["memories"]]
    ids_at_1 = [m["id"] for m in r1.json()["memories"]]

    if len(ids_at_0) >= 2 and len(ids_at_1) >= 1:
        assert ids_at_0[0] != ids_at_1[0]


@pytest.mark.asyncio
async def test_memory_list_offset_beyond_end_returns_empty(auth_client: AsyncClient):
    """An offset beyond all memories must return an empty list, not an error."""
    resp = await auth_client.get("/api/memory?limit=10&offset=999999")
    assert resp.status_code == 200
    assert resp.json()["memories"] == []


@pytest.mark.asyncio
async def test_memory_list_response_schema(auth_client: AsyncClient):
    """Response must include memories, limit, and offset — no more unbounded total."""
    resp = await auth_client.get("/api/memory")
    assert resp.status_code == 200
    data = resp.json()
    assert "memories" in data
    assert "limit" in data
    assert "offset" in data
    # 'total' was removed in favour of pagination; it must not be present
    assert "total" not in data
