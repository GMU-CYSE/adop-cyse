from __future__ import annotations

import pytest

from tests.conftest import open_session, text_of


@pytest.mark.asyncio
async def test_set_then_get_round_trip():
    async with open_session("adop_testbed.servers.memory_server") as session:
        await session.call_tool("memory_set", {"namespace": "reviews", "key": "pkg-a", "value": "looks fine"})
        result = await session.call_tool("memory_get", {"namespace": "reviews", "key": "pkg-a"})
        assert text_of(result) == "looks fine"


@pytest.mark.asyncio
async def test_get_missing_key_does_not_error():
    async with open_session("adop_testbed.servers.memory_server") as session:
        result = await session.call_tool("memory_get", {"namespace": "reviews", "key": "does-not-exist"})
        assert not result.is_error
        assert "no value stored" in text_of(result)


@pytest.mark.asyncio
async def test_list_returns_all_keys_in_namespace():
    async with open_session("adop_testbed.servers.memory_server") as session:
        await session.call_tool("memory_set", {"namespace": "triage", "key": "a", "value": "1"})
        await session.call_tool("memory_set", {"namespace": "triage", "key": "b", "value": "2"})
        result = await session.call_tool("memory_list", {"namespace": "triage"})
        keys = text_of(result).splitlines()
        assert set(keys) == {"a", "b"}


@pytest.mark.asyncio
async def test_persistence_across_separate_sessions():
    """Cross-session persistence is the entire point of the Memory server
    (D.6: 'a durable channel for poisoned content')."""
    async with open_session("adop_testbed.servers.memory_server") as session:
        await session.call_tool("memory_set", {"namespace": "cache", "key": "sticky", "value": "still here"})

    async with open_session("adop_testbed.servers.memory_server") as session:
        result = await session.call_tool("memory_get", {"namespace": "cache", "key": "sticky"})
        assert text_of(result) == "still here"
