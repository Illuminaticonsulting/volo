"""
Unit tests for _FallbackCache — the bounded LRU+TTL in-memory fallback
used by CacheService when Redis is unavailable.
"""
import time

from app.services.cache import _FallbackCache


# ── Basic get/set/delete ──────────────────────────────────────────────────────

def test_basic_set_get():
    c = _FallbackCache()
    c.set("k", "v")
    assert c.get("k") == "v"


def test_missing_key_returns_none():
    c = _FallbackCache()
    assert c.get("missing") is None


def test_delete_removes_key():
    c = _FallbackCache()
    c.set("k", "v")
    c.delete("k")
    assert c.get("k") is None


def test_delete_nonexistent_is_noop():
    c = _FallbackCache()
    c.delete("never-set")  # must not raise


def test_overwrite_updates_value():
    c = _FallbackCache()
    c.set("k", "v1")
    c.set("k", "v2")
    assert c.get("k") == "v2"


# ── TTL ───────────────────────────────────────────────────────────────────────

def test_ttl_zero_expires_immediately():
    c = _FallbackCache()
    c.set("k", "v", ttl=0)
    time.sleep(0.02)
    assert c.get("k") is None


def test_no_ttl_does_not_expire():
    c = _FallbackCache()
    c.set("k", "v")
    time.sleep(0.02)
    assert c.get("k") == "v"


def test_expire_sets_ttl_on_existing_key():
    c = _FallbackCache()
    c.set("k", "v")
    c.expire("k", ttl=0)
    time.sleep(0.02)
    assert c.get("k") is None


def test_expire_nonexistent_key_is_noop():
    c = _FallbackCache()
    c.expire("never-set", ttl=60)  # must not raise


# ── incr ──────────────────────────────────────────────────────────────────────

def test_incr_starts_at_one():
    c = _FallbackCache()
    assert c.incr("ctr") == 1


def test_incr_accumulates():
    c = _FallbackCache()
    c.incr("ctr")
    c.incr("ctr")
    assert c.incr("ctr") == 3


def test_incr_custom_amount():
    c = _FallbackCache()
    assert c.incr("ctr", amount=5) == 5
    assert c.incr("ctr", amount=3) == 8


def test_incr_preserves_ttl():
    """incr() must not reset the existing TTL of a rate-limit key."""
    c = _FallbackCache()
    c.set("rate:x", "0", ttl=60)
    c.incr("rate:x")
    _, expires_at = c._data["rate:x"]
    assert expires_at is not None


def test_incr_on_expired_key_starts_fresh():
    c = _FallbackCache()
    c.set("rate:x", "5", ttl=0)
    time.sleep(0.02)
    # Key expired — incr should start from 0
    assert c.incr("rate:x") == 1


# ── LRU eviction ─────────────────────────────────────────────────────────────

def test_lru_eviction_drops_least_recently_used():
    c = _FallbackCache(maxsize=3)
    c.set("a", "1")
    c.set("b", "2")
    c.set("c", "3")
    # Touch "a" and "c", making "b" the LRU
    c.get("a")
    c.get("c")
    # Adding "d" should evict "b"
    c.set("d", "4")
    assert c.get("b") is None
    assert c.get("a") == "1"
    assert c.get("c") == "3"
    assert c.get("d") == "4"


def test_size_cap_never_exceeded():
    c = _FallbackCache(maxsize=50)
    for i in range(200):
        c.set(f"key:{i}", str(i))
    assert len(c._data) == 50


def test_overwrite_does_not_grow_size():
    c = _FallbackCache(maxsize=3)
    c.set("a", "1")
    c.set("b", "2")
    c.set("c", "3")
    c.set("a", "updated")  # overwrite, not a new key
    assert len(c._data) == 3
    assert c.get("a") == "updated"


def test_full_cache_rate_limit_simulation():
    """Simulate the real rate-limiter pattern: set key, expire, incr, expire."""
    c = _FallbackCache(maxsize=10_000)
    count = c.incr("rate:1.2.3.4")
    assert count == 1
    c.expire("rate:1.2.3.4", ttl=60)
    # Subsequent increments within the window
    for _ in range(59):
        c.incr("rate:1.2.3.4")
    assert c.incr("rate:1.2.3.4") == 61  # over limit
    # TTL still set
    _, expires_at = c._data["rate:1.2.3.4"]
    assert expires_at is not None
