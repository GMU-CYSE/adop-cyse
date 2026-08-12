from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from adop_testbed.sandbox import PROJECT_ROOT
from adop_testbed.scripts.reset_testbed import reset_testbed


@pytest.fixture(autouse=True)
def _reset_testbed_around_each_test():
    """Every test starts and ends against the pristine baseline, so tests
    that stage/commit/write can't bleed into each other or into a
    subsequent `generate_corpus` run.
    """
    reset_testbed()
    yield
    reset_testbed()


@asynccontextmanager
async def open_session(server_module: str) -> AsyncIterator[ClientSession]:
    """Spawn one pinned MCP server as a child process over stdio and yield a
    connected, initialized client session to it.
    """
    params = StdioServerParameters(command=sys.executable, args=["-m", server_module], cwd=str(PROJECT_ROOT))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


def text_of(result) -> str:
    """Extract concatenated text content from a CallToolResult."""
    return "\n".join(block.text for block in result.content if getattr(block, "type", None) == "text")
