from __future__ import annotations

import json

import pytest

from adop_testbed.audit.logger import AuditLogger, SessionSequencer
from adop_testbed.host.agent_host import AgentHost, load_tasks
from adop_testbed.sandbox import PROJECT_ROOT


def test_load_tasks_matches_notebook_categories():
    tasks = load_tasks()
    assert len(tasks) == 6
    categories = {t.category for t in tasks}
    assert categories == {"issue_triage", "patch_drafting", "documentation_summarization"}
    assert sum(1 for t in tasks if t.scenario_tag == "clean") == 3
    assert sum(1 for t in tasks if t.scenario_tag == "poisoned") == 3


@pytest.mark.asyncio
async def test_full_task_set_runs_end_to_end(tmp_path):
    sequencer = SessionSequencer()
    clean_logger = AuditLogger(tmp_path / "clean.jsonl", session_id="itest-01", sequencer=sequencer)
    poisoned_logger = AuditLogger(tmp_path / "poisoned.jsonl", session_id="itest-01", sequencer=sequencer)
    await clean_logger.init()
    await poisoned_logger.init()

    tasks = load_tasks()
    async with AgentHost({"clean": clean_logger, "poisoned": poisoned_logger}) as host:
        await host.run(tasks)

    clean_records = [json.loads(line) for line in (tmp_path / "clean.jsonl").read_text().splitlines()]
    poisoned_records = [json.loads(line) for line in (tmp_path / "poisoned.jsonl").read_text().splitlines()]

    assert all(r["scenario_tag"] == "clean" for r in clean_records)
    assert all(r["scenario_tag"] == "poisoned" for r in poisoned_records)
    assert all(r["result_status"] == "success" for r in clean_records + poisoned_records)

    # The injection chain in task-04 must have actually fired: the scripted
    # plan always follows poisoned-readme.md's embedded instructions, so the
    # generic annotator should catch both the trigger (the fetch) and the
    # argument-injection call it leads to, and propagate post_injection_context
    # to every later call in that same task.
    fetch_records = [r for r in poisoned_records if r["tool_name"] == "fetch"]
    assert any("untrusted_content_source" in r["annotations"] for r in fetch_records)

    diff_records = [r for r in poisoned_records if r["tool_name"] == "git_diff"]
    assert any(
        "argument_injection" in r["annotations"] and "cve-2025-68144" in r["annotations"] for r in diff_records
    )

    post_injection = [r for r in poisoned_records if "post_injection_context" in r.get("annotations", [])]
    assert len(post_injection) >= 3  # every call in task-04 after the poisoned fetch

    # seq is monotonic and shared across both files for one session_id.
    all_seq = sorted(r["seq"] for r in clean_records + poisoned_records)
    assert all_seq == list(range(1, len(all_seq) + 1))


@pytest.mark.asyncio
async def test_unknown_task_id_raises():
    from adop_testbed.types import SyntheticTask

    logger = AuditLogger(PROJECT_ROOT / "corpus" / "_test_scratch.jsonl", session_id="itest-02")
    await logger.init()
    bogus = SyntheticTask(
        id="task-does-not-exist",
        scenario_tag="clean",
        category="issue_triage",
        title="x",
        description="x",
        instruction="x",
    )
    async with AgentHost({"clean": logger, "poisoned": logger}) as host:
        with pytest.raises(KeyError):
            await host.run([bogus])
    logger.out_file.unlink(missing_ok=True)
