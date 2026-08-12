#!/usr/bin/env python3
"""Generates the frozen log corpus (Section G.1/G.2).

Resets the testbed to its pristine baseline, then runs the full fixed
synthetic task set (host/tasks/synthetic_tasks.json) through the agent host
against the four pinned MCP servers, exactly once, in task-set order. Every
tool call the agent host makes is captured by the Observability and Audit
Layer and split, by scenario_tag, into:

    corpus/clean/session-01.jsonl
    corpus/poisoned/session-01.jsonl

Both files share one session_id, since they come from a single run of the
agent host -- a realistic session mixes routine and adversarial tasks, and
that is exactly what the frozen corpus should look like.

Run with: python -m adop_testbed.scripts.generate_corpus
"""

from __future__ import annotations

import asyncio

from adop_testbed.audit.logger import AuditLogger, SessionSequencer
from adop_testbed.host.agent_host import AgentHost, load_tasks
from adop_testbed.sandbox import PROJECT_ROOT
from adop_testbed.scripts.reset_testbed import reset_testbed

SESSION_ID = "session-01"


async def main() -> None:
    reset_testbed()

    sequencer = SessionSequencer()
    clean_logger = AuditLogger(PROJECT_ROOT / "corpus" / "clean" / f"{SESSION_ID}.jsonl", session_id=SESSION_ID, sequencer=sequencer)
    poisoned_logger = AuditLogger(PROJECT_ROOT / "corpus" / "poisoned" / f"{SESSION_ID}.jsonl", session_id=SESSION_ID, sequencer=sequencer)
    for logger in (clean_logger, poisoned_logger):
        # Corpus files are regenerated from scratch each run, not appended to.
        if logger.out_file.exists():
            logger.out_file.unlink()
        await logger.init()

    tasks = load_tasks()
    async with AgentHost({"clean": clean_logger, "poisoned": poisoned_logger}) as host:
        await host.run(tasks)

    print(f"Wrote {clean_logger.out_file.relative_to(PROJECT_ROOT)} ({clean_logger.count} records)")
    print(f"Wrote {poisoned_logger.out_file.relative_to(PROJECT_ROOT)} ({poisoned_logger.count} records)")


if __name__ == "__main__":
    asyncio.run(main())
