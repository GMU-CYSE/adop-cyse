from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from adop_testbed.audit.logger import AuditLogger, SessionSequencer
from adop_testbed.host.agent_host import load_tasks
from adop_testbed.host.llm_agent_host import DEFAULT_MODEL, MAX_TOOL_TURNS, OllamaLiveAgentHost

TASK_01 = next(t for t in load_tasks() if t.id == "task-01-triage-issue-142")


def _msg(content: str = "", tool_calls: list | None = None):
    return SimpleNamespace(content=content, tool_calls=tool_calls or [])


def _tool_call(name: str, arguments: dict):
    return SimpleNamespace(function=SimpleNamespace(name=name, arguments=arguments))


class ScriptedOllamaClient:
    """Fake ollama.AsyncClient.chat(): returns each response in order, so the
    tool-dispatch plumbing in OllamaLiveAgentHost can be tested without a
    real, locally-running model.
    """

    def __init__(self, responses: list) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    async def chat(self, *, model, messages, tools):
        self.calls.append({"model": model, "messages": list(messages), "tools": tools})
        return SimpleNamespace(message=self._responses.pop(0))


@pytest.fixture
async def loggers(tmp_path):
    sequencer = SessionSequencer()
    clean = AuditLogger(tmp_path / "clean.jsonl", session_id="llm-test", sequencer=sequencer)
    poisoned = AuditLogger(tmp_path / "poisoned.jsonl", session_id="llm-test", sequencer=sequencer)
    await clean.init()
    await poisoned.init()
    return {"clean": clean, "poisoned": poisoned}


@pytest.mark.asyncio
async def test_tool_index_is_built_from_the_real_pinned_servers(loggers):
    async with OllamaLiveAgentHost(loggers, client=ScriptedOllamaClient([])) as host:
        names = set(host._tool_index.keys())
    assert {"filesystem__read_text_file", "git__git_diff", "fetch__fetch", "memory__memory_set"} <= names


@pytest.mark.asyncio
async def test_tool_call_round_trip_and_argument_filtering(loggers):
    fake_client = ScriptedOllamaClient(
        [
            _msg(tool_calls=[_tool_call("git__git_status", {"paths": "[]", "unexpected_hallucinated_arg": True})]),
            _msg(content="Status checked; nothing else to do."),
        ]
    )

    async with OllamaLiveAgentHost(loggers, client=fake_client) as host:
        summary = await host.run_task_live(TASK_01)

    assert summary == "Status checked; nothing else to do."
    assert len(fake_client.calls) == 2

    records = [json.loads(line) for line in loggers["clean"].out_file.read_text().splitlines()]
    assert len(records) == 1
    assert records[0]["server"] == "git"
    assert records[0]["tool_name"] == "git_status"
    # git_status takes no parameters -- the hallucinated extra args must be
    # dropped before the call reaches the real MCP server.
    assert records[0]["arguments"] == {}
    assert records[0]["result_status"] == "success"


@pytest.mark.asyncio
async def test_unknown_tool_name_does_not_crash_the_loop(loggers):
    fake_client = ScriptedOllamaClient(
        [
            _msg(tool_calls=[_tool_call("nonexistent_server__nonexistent_tool", {})]),
            _msg(content="done"),
        ]
    )
    async with OllamaLiveAgentHost(loggers, client=fake_client) as host:
        summary = await host.run_task_live(TASK_01)
    assert summary == "done"


@pytest.mark.asyncio
async def test_max_turns_reached_returns_placeholder_instead_of_looping_forever(loggers):
    responses = [_msg(tool_calls=[_tool_call("git__git_status", {})]) for _ in range(MAX_TOOL_TURNS)]
    fake_client = ScriptedOllamaClient(responses)
    async with OllamaLiveAgentHost(loggers, client=fake_client) as host:
        summary = await host.run_task_live(TASK_01)
    assert "max tool-call turns" in summary


@pytest.mark.asyncio
async def test_target_resource_guessing():
    from adop_testbed.host.llm_agent_host import OllamaLiveAgentHost as Host

    assert Host._guess_target_resource({"path": "src/checkout.js"}, "filesystem", "read_text_file") == "src/checkout.js"
    assert Host._guess_target_resource({"url": "https://intranet.example/x"}, "fetch", "fetch") == "https://intranet.example/x"
    assert Host._guess_target_resource({"namespace": "triage", "key": "a"}, "memory", "memory_set") == "memory://triage/a"
    assert Host._guess_target_resource({}, "git", "git_status") == "git:git_status"


# ---------------------------------------------------------------------------
# Real, end-to-end Ollama test. Skips automatically if Ollama isn't running
# or the configured model hasn't been pulled -- run `pytest -m live_llm` to
# select just this test once your local Ollama setup is ready.
# ---------------------------------------------------------------------------


def _real_ollama_ready(model: str) -> bool:
    try:
        import ollama

        tags = ollama.Client().list()
        return any(m.model == model or m.model == f"{model}" for m in tags.models)
    except Exception:
        return False


@pytest.mark.live_llm
@pytest.mark.asyncio
async def test_real_ollama_completes_a_simple_task(loggers):
    import os

    model = os.environ.get("ADOP_OLLAMA_MODEL", DEFAULT_MODEL)
    if not _real_ollama_ready(model):
        pytest.skip(f"Ollama not reachable or model {model!r} not pulled; run `ollama pull {model}`.")

    async with OllamaLiveAgentHost(loggers, model=model) as host:
        summary = await host.run_task_live(TASK_01)

    assert isinstance(summary, str) and summary.strip()
    records = [json.loads(line) for line in loggers["clean"].out_file.read_text().splitlines()]
    assert len(records) >= 1
