from __future__ import annotations

import json

import pytest

from adop_testbed.audit.logger import AuditLogger
from adop_testbed.host.agent_host import load_tasks
from adop_testbed.scripts.live_mode import LIVE_MODE_TASK_IDS, LiveModeViolation, ReadOnlyAgentHost
from adop_testbed.sandbox import PROJECT_ROOT, REPO_ROOT


@pytest.mark.asyncio
async def test_read_only_host_refuses_mutating_tool(tmp_path):
    logger = AuditLogger(tmp_path / "live.jsonl", session_id="live-test")
    await logger.init()
    tasks = {t.id: t for t in load_tasks()}
    mutating_task = tasks["task-02-patch-checkout-db"]  # writes + commits: not allowed in live mode

    async with ReadOnlyAgentHost({"clean": logger, "poisoned": logger}) as host:
        with pytest.raises(LiveModeViolation):
            await host.run([mutating_task])


@pytest.mark.asyncio
async def test_read_only_host_allows_designated_live_tasks(tmp_path):
    logger = AuditLogger(tmp_path / "live.jsonl", session_id="live-test")
    await logger.init()
    tasks = [t for t in load_tasks() if t.id in LIVE_MODE_TASK_IDS]
    assert tasks, "expected at least one task designated safe for live mode"

    async with ReadOnlyAgentHost({"clean": logger, "poisoned": logger}) as host:
        await host.run(tasks)

    records = [json.loads(line) for line in (tmp_path / "live.jsonl").read_text().splitlines()]
    assert all(r["result_status"] == "success" for r in records)


@pytest.mark.asyncio
async def test_live_mode_main_leaves_testbed_at_baseline():
    from adop_testbed.scripts.live_mode import main

    live_demo_dir = PROJECT_ROOT / "corpus" / "live-demo"
    before = set(live_demo_dir.glob("*.jsonl")) if live_demo_dir.exists() else set()

    await main()

    import subprocess

    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=str(REPO_ROOT), capture_output=True, text=True, check=True
    ).stdout
    assert status.strip() == ""

    # This is optional, ungraded demo output (G.2); don't leave it behind for
    # the schema tests or a future `git status` to trip over.
    for new_file in set(live_demo_dir.glob("*.jsonl")) - before:
        new_file.unlink()
