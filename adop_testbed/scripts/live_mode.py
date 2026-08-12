#!/usr/bin/env python3
"""Live mode (Section G.2): an optional, READ-ONLY harness for the final PoC
demo. It runs the agent host against the live, pinned reference servers to
produce a fresh demo session, without ever writing back into the frozen
baseline.

This is enforced two ways:
  1. Only the read-only subset of tools is permitted (see READ_ONLY_TOOLS
     below) -- any task plan that calls a write/commit/init tool is refused.
  2. The testbed is reset to baseline again immediately afterwards, so a
     live-mode run can never leave residue for the next team or the next
     grading pass.

Live mode does NOT replace the static corpus for grading (G.2); it exists
solely so a team's own Student-Developed Agent Trust and Assurance Tool can
be pointed at a live session during the final demo.

Run with: python -m adop_testbed.scripts.live_mode
"""

from __future__ import annotations

import asyncio
import uuid

from adop_testbed.audit.logger import AuditLogger
from adop_testbed.host.agent_host import AgentHost, load_tasks
from adop_testbed.sandbox import PROJECT_ROOT
from adop_testbed.scripts.reset_testbed import reset_testbed

# Tools that never mutate the frozen synthetic-repository baseline. Memory
# writes are permitted: the cross-session store is not part of ADOP's core
# baseline (G.1's pinned servers, synthetic repository, and task set), so
# recording notes there during a live demo leaves no residue that would
# affect another team's static-mode grading run.
ALLOWED_IN_LIVE_MODE = {
    "filesystem": {"read_text_file", "list_directory", "search_files", "get_file_info"},
    "git": {"git_status", "git_log", "git_branch", "git_show_worktree", "git_diff"},
    "fetch": {"fetch", "list_available_pages"},
    "memory": {"memory_get", "memory_list", "memory_set"},
}

# Only tasks whose scripted plan stays within ALLOWED_IN_LIVE_MODE are
# meaningful in live mode. task-02 and task-05 draft patches and commit;
# task-04 and task-06 deliberately reproduce the CVEs via a write/init --
# all four are Static-mode-only by design.
LIVE_MODE_TASK_IDS = {"task-01-triage-issue-142", "task-03-summarize-vendor-readme"}


class LiveModeViolation(Exception):
    """Raised when a task plan would perform a write against the live baseline."""


class ReadOnlyAgentHost(AgentHost):
    async def call(self, task, server, tool_name, arguments, *, target_resource, annotations=None):  # type: ignore[override]
        if tool_name not in ALLOWED_IN_LIVE_MODE.get(server, set()):
            raise LiveModeViolation(
                f"Live mode may not mutate ADOP's core; refusing to call {server}.{tool_name} "
                f"(task {task.id}). Use Static mode for tasks that write, commit, or "
                f"initialize repositories."
            )
        return await super().call(task, server, tool_name, arguments, target_resource=target_resource, annotations=annotations)


async def main() -> None:
    session_id = f"live-{uuid.uuid4().hex[:8]}"
    out_file = PROJECT_ROOT / "corpus" / "live-demo" / f"{session_id}.jsonl"
    logger = AuditLogger(out_file, session_id=session_id)
    await logger.init()

    tasks = [t for t in load_tasks() if t.id in LIVE_MODE_TASK_IDS]

    try:
        async with ReadOnlyAgentHost({"clean": logger, "poisoned": logger}) as host:
            await host.run(tasks)
    finally:
        reset_testbed()

    print(f"Live-mode demo session written to {out_file.relative_to(PROJECT_ROOT)} ({logger.count} records).")
    print("Testbed reset back to baseline; no residue left for other teams.")


if __name__ == "__main__":
    asyncio.run(main())
