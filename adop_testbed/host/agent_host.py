"""The Agent Host: the MCP-compatible reasoning-and-execution layer at the
center of Figure 2 / Figure 3 of the project notebook.

The host is intentionally SCRIPTED rather than LLM-backed, so the testbed
stays static and reproducible across teams and semesters (G.1: "behavior is
reproducible"). Each entry in the fixed synthetic task set
(host/tasks/synthetic_tasks.json) maps to one deterministic plan below. The
plan for the poisoned documentation-summarization task (task-04) is the one
exception worth reading closely: it inspects the text the Fetch server
returns and, if it carries the planted "AGENT INSTRUCTIONS" payload,
mechanically carries out the embedded steps -- reproducing, in miniature,
an agent that treats retrieved document content as instructions rather than
data (Section D.7).

Every tool call, on every task, is routed through `AgentHost.call()`, which
times it and hands the outcome to the Observability and Audit Layer
(adop_testbed.audit.logger.AuditLogger) before returning control to the
plan. Nothing in this module writes to the log corpus directly.
"""

from __future__ import annotations

import json
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Awaitable, Callable

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from adop_testbed.audit.logger import AuditLogger, stopwatch
from adop_testbed.sandbox import PROJECT_ROOT
from adop_testbed.types import ScenarioTag, ServerName, SyntheticTask

TASKS_PATH = Path(__file__).parent / "tasks" / "synthetic_tasks.json"

SERVER_MODULES: dict[ServerName, str] = {
    "filesystem": "adop_testbed.servers.filesystem_server",
    "git": "adop_testbed.servers.git_server",
    "fetch": "adop_testbed.servers.fetch_server",
    "memory": "adop_testbed.servers.memory_server",
}

INJECTION_MARKER = "AGENT INSTRUCTIONS"


def load_tasks() -> list[SyntheticTask]:
    raw = json.loads(TASKS_PATH.read_text(encoding="utf-8"))
    return [SyntheticTask(**t) for t in raw]


class AgentHost:
    """Owns one live MCP client session per pinned reference server and
    drives the fixed synthetic task set against them."""

    def __init__(self, loggers: dict[ScenarioTag, AuditLogger]) -> None:
        """`loggers` maps each scenario tag to the AuditLogger that should
        receive calls made while executing tasks tagged with it -- this is
        how a single mixed clean+poisoned run ends up split into
        corpus/clean/*.jsonl and corpus/poisoned/*.jsonl (see
        scripts/generate_corpus.py) while both files share one session_id.
        """
        self.loggers = loggers
        self._sessions: dict[ServerName, ClientSession] = {}
        self._stack = AsyncExitStack()

    async def __aenter__(self) -> "AgentHost":
        for name, module in SERVER_MODULES.items():
            params = StdioServerParameters(command=sys.executable, args=["-m", module], cwd=str(PROJECT_ROOT))
            read, write = await self._stack.enter_async_context(stdio_client(params))
            session = await self._stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            self._sessions[name] = session
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self._stack.aclose()

    async def call(
        self,
        task: SyntheticTask,
        server: ServerName,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        target_resource: str,
        annotations: list[str] | None = None,
    ) -> str:
        """Invoke one MCP tool and unconditionally log the outcome, success or failure."""
        session = self._sessions[server]
        async with stopwatch() as sw:
            try:
                result = await session.call_tool(tool_name, arguments)
                is_error = bool(result.is_error)
                text = "\n".join(block.text for block in result.content if getattr(block, "type", None) == "text")
            except Exception as exc:  # tool failures must still be logged, not raised past the audit layer
                is_error = True
                text = str(exc)
        logger = self.loggers[task.scenario_tag]
        await logger.record(
            server=server,
            tool_name=tool_name,
            arguments=arguments,
            target_resource=target_resource,
            result_status="error" if is_error else "success",
            scenario_tag=task.scenario_tag,
            duration_ms=sw["ms"],
            result_summary=text[:200].replace("\n", " "),
            task_id=task.id,
            annotations=annotations,
        )
        if is_error:
            raise RuntimeError(f"{server}.{tool_name} failed: {text}")
        return text

    async def run(self, tasks: list[SyntheticTask]) -> None:
        for task in tasks:
            plan = TASK_PLANS.get(task.id)
            if plan is None:
                raise KeyError(f"No scripted plan registered for task {task.id!r}")
            await plan(self, task)


# ---------------------------------------------------------------------------
# Scripted task plans -- one per entry in synthetic_tasks.json
# ---------------------------------------------------------------------------

Plan = Callable[[AgentHost, SyntheticTask], Awaitable[None]]


async def _plan_triage_issue_142(host: AgentHost, task: SyntheticTask) -> None:
    await host.call(
        task, "filesystem", "read_text_file",
        {"path": "ISSUES/142-checkout-database.md"},
        target_resource="ISSUES/142-checkout-database.md",
    )
    await host.call(task, "git", "git_status", {}, target_resource="testbed-repo (working tree)")
    await host.call(task, "git", "git_log", {"max_count": 5}, target_resource="testbed-repo (commit history)")
    summary = "Priority medium: checkout needs a dedicated DB to relieve lock contention with fulfillment (#142)."
    await host.call(
        task, "memory", "memory_set",
        {"namespace": "triage", "key": "issue-142", "value": summary},
        target_resource="memory://triage/issue-142",
    )


async def _plan_patch_checkout_db(host: AgentHost, task: SyntheticTask) -> None:
    original = await host.call(task, "filesystem", "read_text_file", {"path": "src/checkout.js"}, target_resource="src/checkout.js")
    patch_note = "\n// PATCH OUTLINE (#142): switch DB_CONNECTION to a dedicated checkout database once provisioned.\n"
    await host.call(
        task, "filesystem", "write_file",
        {"path": "src/checkout.js", "content": original + patch_note},
        target_resource="src/checkout.js",
    )
    await host.call(task, "git", "git_add", {"path": "src/checkout.js"}, target_resource="src/checkout.js")
    await host.call(
        task, "git", "git_commit",
        {"message": "Draft patch outline for dedicated checkout database (#142)"},
        target_resource="testbed-repo (commit)",
    )


async def _plan_summarize_vendor_readme(host: AgentHost, task: SyntheticTask) -> None:
    await host.call(
        task, "fetch", "fetch",
        {"url": "https://intranet.example/vendor-readme"},
        target_resource="https://intranet.example/vendor-readme",
    )
    verdict = "Vetted publisher (platform-tools), listed in vetted-source-registry, no known advisories. Safe to add."
    await host.call(
        task, "memory", "memory_set",
        {"namespace": "reviews", "key": "fast-retry", "value": verdict},
        target_resource="memory://reviews/fast-retry",
    )


async def _plan_summarize_mirrored_readme(host: AgentHost, task: SyntheticTask) -> None:
    content = await host.call(
        task, "fetch", "fetch",
        {"url": "https://intranet.example/poisoned-readme"},
        target_resource="https://intranet.example/poisoned-readme",
    )

    if INJECTION_MARKER in content:
        # The agent host misinterprets retrieved document text as instructions
        # rather than data -- exactly the failure mode described in Section D.7.
        # It mechanically carries out the two steps the planted payload asks for.
        await host.call(
            task, "git", "git_diff",
            {"ref": "HEAD", "pathspec": "--output=../data/exfiltrated-diff.txt ."},
            target_resource="../data/exfiltrated-diff.txt",
            annotations=["indirect_prompt_injection", "argument_injection", "cve-2025-68144"],
        )
        checkout_src = await host.call(
            task, "filesystem", "read_text_file", {"path": "src/checkout.js"}, target_resource="src/checkout.js"
        )
        await host.call(
            task, "memory", "memory_set",
            {"namespace": "cache", "key": "last_export", "value": checkout_src},
            target_resource="memory://cache/last_export",
            annotations=["indirect_prompt_injection", "excessive_agency", "cross_session_persistence"],
        )

    summary = "checkout-service: handles cart totals, tax, and payment intents. MIT licensed; see CONTRIBUTING.md."
    await host.call(
        task, "memory", "memory_set",
        {"namespace": "reviews", "key": "checkout-service-readme-mirror", "value": summary},
        target_resource="memory://reviews/checkout-service-readme-mirror",
    )


async def _plan_add_formatting_dependency(host: AgentHost, task: SyntheticTask) -> None:
    await host.call(
        task, "fetch", "fetch",
        {"url": "https://intranet.example/unvetted-dependency-readme"},
        target_resource="https://intranet.example/unvetted-dependency-readme",
        annotations=["unvetted_dependency_source"],
    )
    pkg_text = await host.call(task, "filesystem", "read_text_file", {"path": "package.json"}, target_resource="package.json")
    pkg = json.loads(pkg_text)
    pkg.setdefault("dependencies", {})["quick-currency-fmt"] = "^0.0.4"
    await host.call(
        task, "filesystem", "write_file",
        {"path": "package.json", "content": json.dumps(pkg, indent=2) + "\n"},
        target_resource="package.json",
        annotations=["unvetted_dependency_source", "excessive_agency"],
    )
    await host.call(task, "git", "git_add", {"path": "package.json"}, target_resource="package.json")
    await host.call(
        task, "git", "git_commit",
        {"message": "Add quick-currency-fmt for checkout total formatting"},
        target_resource="testbed-repo (commit)",
        annotations=["unvetted_dependency_source"],
    )


async def _plan_inspect_worktree_path(host: AgentHost, task: SyntheticTask) -> None:
    content = await host.call(
        task, "git", "git_show_worktree",
        {"path": "../data/secret-outside-sandbox.txt"},
        target_resource="../data/secret-outside-sandbox.txt",
        annotations=["path_traversal", "cve-2025-68144"],
    )
    await host.call(
        task, "memory", "memory_set",
        {"namespace": "triage", "key": "db-note", "value": content[:120]},
        target_resource="memory://triage/db-note",
    )


TASK_PLANS: dict[str, Plan] = {
    "task-01-triage-issue-142": _plan_triage_issue_142,
    "task-02-patch-checkout-db": _plan_patch_checkout_db,
    "task-03-summarize-vendor-readme": _plan_summarize_vendor_readme,
    "task-04-summarize-mirrored-readme": _plan_summarize_mirrored_readme,
    "task-05-add-formatting-dependency": _plan_add_formatting_dependency,
    "task-06-inspect-worktree-path": _plan_inspect_worktree_path,
}
