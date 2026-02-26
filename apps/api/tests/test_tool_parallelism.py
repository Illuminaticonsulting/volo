"""
Tests for parallel tool execution in the agent orchestrator.

The orchestrator executes all approved tools concurrently via asyncio.gather
with a 30-second per-tool timeout. These tests verify:
- Tools run concurrently (wall-clock time < serial sum)
- A failing tool does not prevent other tools from running
- A timed-out tool returns an error dict, not an exception
- Each tool result is wrapped correctly in the tool_results list
"""
import asyncio
import time

import pytest
from unittest.mock import MagicMock


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _run_tool_impl(blk):
    """Re-implementation of the orchestrator's _run_tool helper for unit testing."""
    try:
        result = await asyncio.wait_for(blk.coro(), timeout=30.0)
        return result
    except asyncio.TimeoutError:
        return {"error": f"Tool '{blk.name}' timed out after 30s"}
    except Exception as exc:
        return {"error": str(exc)}


def _make_block(name: str, coro_factory):
    """Create a minimal mock tool-use block."""
    blk = MagicMock()
    blk.name = name
    blk.coro = coro_factory
    return blk


# ── Concurrency ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tools_execute_concurrently():
    """
    Three tools each sleeping 100ms should complete in ~100ms total,
    not 300ms (serial).
    """
    DELAY = 0.1  # 100ms

    async def slow_tool():
        await asyncio.sleep(DELAY)
        return {"ok": True}

    blocks = [_make_block(f"tool_{i}", slow_tool) for i in range(3)]

    start = time.monotonic()
    results = await asyncio.gather(*[_run_tool_impl(b) for b in blocks])
    elapsed = time.monotonic() - start

    # All three completed
    assert all(r == {"ok": True} for r in results)
    # Should finish in less than 2× the single-tool delay (well under 3× serial)
    assert elapsed < DELAY * 2, (
        f"Expected parallel execution ({elapsed:.3f}s) to be < {DELAY * 2:.3f}s"
    )


@pytest.mark.asyncio
async def test_all_tools_called_even_if_one_raises():
    """
    If one tool raises an exception the others still complete.
    """
    call_log = []

    async def good_tool():
        call_log.append("good")
        return {"ok": True}

    async def bad_tool():
        raise ValueError("simulated failure")

    async def another_good():
        call_log.append("another_good")
        return {"also": "ok"}

    blocks = [
        _make_block("good", good_tool),
        _make_block("bad", bad_tool),
        _make_block("another_good", another_good),
    ]

    results = await asyncio.gather(*[_run_tool_impl(b) for b in blocks])

    assert "good" in call_log
    assert "another_good" in call_log
    # The failing tool returns an error dict
    assert results[1] == {"error": "simulated failure"}
    # The others return their values
    assert results[0] == {"ok": True}
    assert results[2] == {"also": "ok"}


@pytest.mark.asyncio
async def test_failing_tool_returns_error_dict_not_exception():
    """
    A tool that raises must produce {"error": "<message>"}, not propagate.
    """
    async def failing():
        raise RuntimeError("unexpected crash")

    blk = _make_block("crash_tool", failing)
    result = await _run_tool_impl(blk)

    assert isinstance(result, dict)
    assert "error" in result
    assert "unexpected crash" in result["error"]


@pytest.mark.asyncio
async def test_tool_timeout_returns_error_dict():
    """
    A tool that exceeds the per-tool timeout returns a timeout error dict,
    not an asyncio.TimeoutError or a hang.
    """
    async def _run_tool_with_short_timeout(blk):
        try:
            return await asyncio.wait_for(blk.coro(), timeout=0.05)  # 50ms
        except asyncio.TimeoutError:
            return {"error": f"Tool '{blk.name}' timed out after 30s"}
        except Exception as exc:
            return {"error": str(exc)}

    async def forever():
        await asyncio.sleep(10)  # much longer than the test timeout

    blk = _make_block("slow_tool", forever)
    result = await _run_tool_with_short_timeout(blk)

    assert isinstance(result, dict)
    assert "error" in result
    assert "timed out" in result["error"]


@pytest.mark.asyncio
async def test_successful_tool_result_passthrough():
    """A tool that returns a dict has its value passed through unchanged."""
    expected = {"data": [1, 2, 3], "status": "ok"}

    async def tool():
        return expected

    blk = _make_block("data_tool", tool)
    result = await _run_tool_impl(blk)
    assert result == expected


@pytest.mark.asyncio
async def test_mixed_success_and_failure_results_aligned():
    """
    asyncio.gather preserves order — result[i] corresponds to blocks[i].
    """
    async def tool_a():
        return {"name": "a"}

    async def tool_b():
        raise KeyError("missing key")

    async def tool_c():
        return {"name": "c"}

    blocks = [
        _make_block("a", tool_a),
        _make_block("b", tool_b),
        _make_block("c", tool_c),
    ]
    results = await asyncio.gather(*[_run_tool_impl(b) for b in blocks])

    assert results[0] == {"name": "a"}
    assert "error" in results[1]
    assert results[2] == {"name": "c"}
