"""
Tests for conversation list caching and message pagination.
- Cache hit: pre-populated key is served without a DB round-trip
- Cache miss: DB is queried and key is populated
- Invalidation: create / delete / update clear the cache
- Message pagination: msg_limit / msg_offset slice correctly
"""
import pytest
from httpx import AsyncClient

from app.routes.conversations import _conv_list_cache_key
from app.services.cache import cache


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _clear_conv_cache(user_id: str = "dev-user"):
    """Remove all convlist: keys for the given user from the fallback cache."""
    prefix = f"convlist:{user_id}:"
    stale = [k for k in cache._fallback._data if k.startswith(prefix)]
    for k in stale:
        cache._fallback.delete(k)


# ── Cache hit ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cache_hit_returns_sentinel_data(auth_client: AsyncClient):
    """A pre-populated cache entry is served directly without hitting the DB."""
    key = _conv_list_cache_key("dev-user", 50, 0, None)

    sentinel = {
        "conversations": [{"id": "sentinel-id", "title": "From Cache", "pinned": False,
                           "message_count": 0, "preview": "", "created_at": None,
                           "updated_at": None}],
        "total": 1, "limit": 50, "offset": 0,
    }
    await cache.set_json(key, sentinel, ttl=30)

    try:
        resp = await auth_client.get("/api/conversations?limit=50&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["conversations"][0]["id"] == "sentinel-id"
    finally:
        await cache.delete(key)


@pytest.mark.asyncio
async def test_cache_miss_populates_cache(auth_client: AsyncClient):
    """After a cache miss, the response is stored in the cache."""
    key = _conv_list_cache_key("dev-user", 50, 0, None)
    await cache.delete(key)  # ensure miss

    resp = await auth_client.get("/api/conversations?limit=50&offset=0")
    assert resp.status_code == 200

    cached = await cache.get_json(key)
    assert cached is not None
    assert "conversations" in cached
    assert cached["limit"] == 50
    assert cached["offset"] == 0

    # Cleanup
    await cache.delete(key)


@pytest.mark.asyncio
async def test_two_identical_requests_return_same_data(auth_client: AsyncClient):
    """Both requests return the same payload (second served from cache)."""
    await _clear_conv_cache()

    r1 = await auth_client.get("/api/conversations?limit=50&offset=0")
    r2 = await auth_client.get("/api/conversations?limit=50&offset=0")

    assert r1.status_code == r2.status_code == 200
    assert r1.json() == r2.json()

    await _clear_conv_cache()


# ── Invalidation ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_invalidates_cache(auth_client: AsyncClient):
    """Creating a conversation clears the cached list."""
    await _clear_conv_cache()
    key = _conv_list_cache_key("dev-user", 50, 0, None)

    # Prime the cache
    await auth_client.get("/api/conversations?limit=50&offset=0")
    assert await cache.get_json(key) is not None

    # Create a conversation — must invalidate
    resp = await auth_client.post("/api/conversations", json={"title": "Invalidation Test"})
    assert resp.status_code == 200

    # Cache key must be gone
    assert await cache.get_json(key) is None


@pytest.mark.asyncio
async def test_delete_invalidates_cache(auth_client: AsyncClient):
    """Deleting a conversation clears the cached list."""
    await _clear_conv_cache()
    key = _conv_list_cache_key("dev-user", 50, 0, None)

    create = await auth_client.post("/api/conversations", json={"title": "To Delete"})
    conv_id = create.json()["id"]

    # Prime the cache
    await auth_client.get("/api/conversations?limit=50&offset=0")
    assert await cache.get_json(key) is not None

    await auth_client.delete(f"/api/conversations/{conv_id}")
    assert await cache.get_json(key) is None


@pytest.mark.asyncio
async def test_update_invalidates_cache(auth_client: AsyncClient):
    """Renaming a conversation clears the cached list."""
    await _clear_conv_cache()
    key = _conv_list_cache_key("dev-user", 50, 0, None)

    create = await auth_client.post("/api/conversations", json={"title": "Before Update"})
    conv_id = create.json()["id"]

    # Prime the cache
    await auth_client.get("/api/conversations?limit=50&offset=0")
    assert await cache.get_json(key) is not None

    await auth_client.patch(f"/api/conversations/{conv_id}", json={"title": "After Update"})
    assert await cache.get_json(key) is None

    # Cleanup
    await auth_client.delete(f"/api/conversations/{conv_id}")


@pytest.mark.asyncio
async def test_after_invalidation_fresh_data_is_returned(auth_client: AsyncClient):
    """After cache invalidation a new request returns up-to-date data."""
    await _clear_conv_cache()

    # Initial list count
    r1 = await auth_client.get("/api/conversations?limit=50&offset=0")
    count_before = len(r1.json()["conversations"])

    # Create — invalidates
    create = await auth_client.post("/api/conversations", json={"title": "New Conv"})
    conv_id = create.json()["id"]

    # Next list must reflect the new conversation
    r2 = await auth_client.get("/api/conversations?limit=50&offset=0")
    assert len(r2.json()["conversations"]) == count_before + 1

    # Cleanup
    await auth_client.delete(f"/api/conversations/{conv_id}")
    await _clear_conv_cache()


# ── Message pagination ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_message_pagination_first_page(auth_client: AsyncClient):
    """msg_limit=2&msg_offset=0 returns the first 2 messages."""
    create = await auth_client.post("/api/conversations", json={"title": "Msg Paging"})
    conv_id = create.json()["id"]

    for i in range(4):
        await auth_client.post(
            f"/api/conversations/{conv_id}/messages",
            json={"role": "user", "content": f"Message {i}"},
        )

    resp = await auth_client.get(f"/api/conversations/{conv_id}?msg_limit=2&msg_offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["messages"]) == 2
    assert data["msg_limit"] == 2
    assert data["msg_offset"] == 0

    # Cleanup
    await auth_client.delete(f"/api/conversations/{conv_id}")


@pytest.mark.asyncio
async def test_message_pagination_pages_do_not_overlap(auth_client: AsyncClient):
    """Page 1 and page 2 must return distinct messages."""
    create = await auth_client.post("/api/conversations", json={"title": "Msg Overlap"})
    conv_id = create.json()["id"]

    for i in range(4):
        await auth_client.post(
            f"/api/conversations/{conv_id}/messages",
            json={"role": "user", "content": f"Msg {i}"},
        )

    r1 = await auth_client.get(f"/api/conversations/{conv_id}?msg_limit=2&msg_offset=0")
    r2 = await auth_client.get(f"/api/conversations/{conv_id}?msg_limit=2&msg_offset=2")

    ids1 = {m["id"] for m in r1.json()["messages"]}
    ids2 = {m["id"] for m in r2.json()["messages"]}
    assert ids1.isdisjoint(ids2), "Pages must not share any message IDs"

    # Cleanup
    await auth_client.delete(f"/api/conversations/{conv_id}")


@pytest.mark.asyncio
async def test_message_offset_beyond_end_returns_empty(auth_client: AsyncClient):
    """An offset past the last message returns an empty list, not an error."""
    create = await auth_client.post("/api/conversations", json={"title": "Offset End"})
    conv_id = create.json()["id"]

    await auth_client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"role": "user", "content": "Only message"},
    )

    resp = await auth_client.get(f"/api/conversations/{conv_id}?msg_limit=10&msg_offset=9999")
    assert resp.status_code == 200
    assert resp.json()["messages"] == []

    # Cleanup
    await auth_client.delete(f"/api/conversations/{conv_id}")


@pytest.mark.asyncio
async def test_message_pagination_response_includes_meta(auth_client: AsyncClient):
    """Response must include msg_limit and msg_offset fields."""
    create = await auth_client.post("/api/conversations", json={"title": "Meta Test"})
    conv_id = create.json()["id"]

    resp = await auth_client.get(f"/api/conversations/{conv_id}?msg_limit=25&msg_offset=5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["msg_limit"] == 25
    assert data["msg_offset"] == 5

    # Cleanup
    await auth_client.delete(f"/api/conversations/{conv_id}")
