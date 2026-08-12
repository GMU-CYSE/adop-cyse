from __future__ import annotations

import pytest

from adop_testbed.sandbox import REPO_ROOT
from tests.conftest import open_session, text_of


@pytest.mark.asyncio
async def test_read_text_file():
    async with open_session("adop_testbed.servers.filesystem_server") as session:
        result = await session.call_tool("read_text_file", {"path": "README.md"})
        assert not result.is_error
        assert "checkout-service" in text_of(result)


@pytest.mark.asyncio
async def test_write_then_read_round_trip():
    async with open_session("adop_testbed.servers.filesystem_server") as session:
        await session.call_tool("write_file", {"path": "tmp/note.txt", "content": "hello testbed"})
        result = await session.call_tool("read_text_file", {"path": "tmp/note.txt"})
        assert text_of(result) == "hello testbed"
    assert (REPO_ROOT / "tmp" / "note.txt").exists()


@pytest.mark.asyncio
async def test_list_directory():
    async with open_session("adop_testbed.servers.filesystem_server") as session:
        result = await session.call_tool("list_directory", {"path": "src"})
        listing = text_of(result)
        assert "checkout.js" in listing
        assert "fulfillment.js" in listing


@pytest.mark.asyncio
async def test_search_files():
    async with open_session("adop_testbed.servers.filesystem_server") as session:
        result = await session.call_tool("search_files", {"pattern": "checkout"})
        assert "src/checkout.js" in text_of(result).replace("\\", "/")


@pytest.mark.asyncio
async def test_get_file_info():
    async with open_session("adop_testbed.servers.filesystem_server") as session:
        result = await session.call_tool("get_file_info", {"path": "README.md"})
        assert "is_file" in text_of(result)


@pytest.mark.asyncio
async def test_read_rejects_path_traversal():
    """Unlike the Git server, the Filesystem server must reject an escape attempt."""
    async with open_session("adop_testbed.servers.filesystem_server") as session:
        result = await session.call_tool("read_text_file", {"path": "../data/secret-outside-sandbox.txt"})
        assert result.is_error


@pytest.mark.asyncio
async def test_write_rejects_path_traversal():
    async with open_session("adop_testbed.servers.filesystem_server") as session:
        result = await session.call_tool("write_file", {"path": "../escape.txt", "content": "nope"})
        assert result.is_error
    assert not (REPO_ROOT.parent / "escape.txt").exists()
