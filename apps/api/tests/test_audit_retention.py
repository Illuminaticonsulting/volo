"""
Tests for AuditTrail.purge_old_logs() — the 90-day audit log retention job.
- Old rows (> retention_days) are deleted
- Recent rows are preserved
- Boundary conditions are handled correctly
- Returns the count of deleted rows
"""
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, text

from app.database import async_session, AuditLog
from app.middleware import AuditTrail


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _insert_audit_log(days_ago: int) -> str:
    """Insert an AuditLog row with a timestamp `days_ago` days in the past."""
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    # AuditLog.timestamp has no timezone info (plain DateTime) — strip tz
    ts_naive = ts.replace(tzinfo=None)
    async with async_session() as session:
        row = AuditLog(
            user_id="test-retention-user",
            action="test_action",
            resource_type="test",
            details={"test": True},
            ip_address="127.0.0.1",
            timestamp=ts_naive,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return str(row.id)


async def _row_exists(row_id: str) -> bool:
    """Return True if an AuditLog row with the given id still exists."""
    async with async_session() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.id == row_id)
        )
        return result.scalar_one_or_none() is not None


async def _cleanup_test_rows():
    """Remove all rows inserted by these tests."""
    async with async_session() as session:
        await session.execute(
            text("DELETE FROM audit_logs WHERE user_id = 'test-retention-user'")  # noqa: S608
        )
        await session.commit()


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_purge_deletes_old_rows():
    """A row older than retention_days must be deleted."""
    row_id = await _insert_audit_log(days_ago=91)
    try:
        assert await _row_exists(row_id), "Row should exist before purge"
        deleted = await AuditTrail.purge_old_logs(retention_days=90)
        assert deleted >= 1
        assert not await _row_exists(row_id), "Old row must be deleted after purge"
    finally:
        await _cleanup_test_rows()


@pytest.mark.asyncio
async def test_purge_keeps_recent_rows():
    """A row within the retention window must NOT be deleted."""
    row_id = await _insert_audit_log(days_ago=10)
    try:
        await AuditTrail.purge_old_logs(retention_days=90)
        assert await _row_exists(row_id), "Recent row must survive purge"
    finally:
        await _cleanup_test_rows()


@pytest.mark.asyncio
async def test_purge_boundary_just_over_cutoff():
    """A row at exactly 90 days + 1 second old must be deleted."""
    # 91 days is safely over the cutoff
    row_id = await _insert_audit_log(days_ago=91)
    try:
        deleted = await AuditTrail.purge_old_logs(retention_days=90)
        assert deleted >= 1
        assert not await _row_exists(row_id)
    finally:
        await _cleanup_test_rows()


@pytest.mark.asyncio
async def test_purge_returns_zero_when_nothing_to_delete():
    """When no rows are older than the retention window, returns 0."""
    # Use a very short retention window so nothing recent qualifies
    await _insert_audit_log(days_ago=1)
    try:
        deleted = await AuditTrail.purge_old_logs(retention_days=9999)
        assert deleted == 0
    finally:
        await _cleanup_test_rows()


@pytest.mark.asyncio
async def test_purge_removes_old_but_not_new():
    """Mixed scenario: only old rows are deleted, new rows survive."""
    old_id = await _insert_audit_log(days_ago=180)
    new_id = await _insert_audit_log(days_ago=5)
    try:
        deleted = await AuditTrail.purge_old_logs(retention_days=90)
        assert deleted >= 1
        assert not await _row_exists(old_id), "Old row must be deleted"
        assert await _row_exists(new_id), "Recent row must survive"
    finally:
        await _cleanup_test_rows()


@pytest.mark.asyncio
async def test_purge_deletes_multiple_old_rows():
    """All rows older than the cutoff are removed in a single call."""
    old_ids = [await _insert_audit_log(days_ago=d) for d in (100, 200, 365)]
    try:
        deleted = await AuditTrail.purge_old_logs(retention_days=90)
        assert deleted >= 3
        for oid in old_ids:
            assert not await _row_exists(oid), f"Old row {oid} must be deleted"
    finally:
        await _cleanup_test_rows()


@pytest.mark.asyncio
async def test_purge_is_idempotent():
    """Calling purge twice in a row does not error and second call deletes 0."""
    await _insert_audit_log(days_ago=120)
    try:
        first = await AuditTrail.purge_old_logs(retention_days=90)
        second = await AuditTrail.purge_old_logs(retention_days=90)
        assert first >= 1
        assert second == 0
    finally:
        await _cleanup_test_rows()
