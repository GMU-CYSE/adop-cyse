from __future__ import annotations

import pytest

from tests.conftest import open_session, text_of


@pytest.mark.asyncio
async def test_fetch_clean_page():
    async with open_session("adop_testbed.servers.fetch_server") as session:
        result = await session.call_tool("fetch", {"url": "https://intranet.example/vendor-readme"})
        assert not result.is_error
        assert "fast-retry" in text_of(result)


@pytest.mark.asyncio
async def test_fetch_poisoned_page_returns_raw_content_unfiltered():
    """The Fetch server must not sanitize content -- filtering is out of its
    scope by design (see docs/TRUST_ASSUMPTIONS.md, C1)."""
    async with open_session("adop_testbed.servers.fetch_server") as session:
        result = await session.call_tool("fetch", {"url": "https://intranet.example/poisoned-readme"})
        assert not result.is_error
        assert "AGENT INSTRUCTIONS" in text_of(result)


@pytest.mark.asyncio
async def test_list_available_pages_includes_seeded_pages():
    async with open_session("adop_testbed.servers.fetch_server") as session:
        result = await session.call_tool("list_available_pages", {})
        pages = text_of(result)
        assert "https://intranet.example/poisoned-readme" in pages
        assert "https://intranet.example/vendor-readme" in pages


@pytest.mark.asyncio
async def test_fetch_refuses_non_sandboxed_host():
    async with open_session("adop_testbed.servers.fetch_server") as session:
        result = await session.call_tool("fetch", {"url": "https://evil.example/whatever"})
        assert result.is_error
