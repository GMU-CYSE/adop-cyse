#!/usr/bin/env python3
"""Interactive mode: a live demo CLI on top of the same pinned Agent Host
and MCP servers Live mode uses.

This exists for demoing ADOP (e.g. a Shark Tank-style live session) --
letting a presenter type a free-text instruction and watch the real,
locally-run LLM decide which tools to call against the real, pinned
servers, in real time. It is NOT a replacement for the fixed synthetic
task set: `live_mode` / `generate_corpus` remain the reproducible
benchmark every team's detector is built against (see README.md "The
fixed synthetic task set"). Ad hoc instructions typed here have no fixed
ground truth and are not part of that benchmark.

It builds on `OllamaLiveAgentHost.run_task_live()` exactly as
`live_mode.py` does, wrapping each typed instruction in a `SyntheticTask`
on the fly -- no changes to the agent host or MCP servers were needed or
made.

Requires Ollama running locally with a tool-calling-capable model pulled.
See README.md "Requirements".

Run with: python -m adop_testbed.scripts.interactive_mode [--model MODEL_NAME] [--no-reset]
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import uuid

from adop_testbed.audit.logger import AuditLogger, SessionSequencer
from adop_testbed.host.llm_agent_host import DEFAULT_MODEL, OllamaLiveAgentHost
from adop_testbed.sandbox import PROJECT_ROOT
from adop_testbed.scripts.reset_testbed import reset_testbed
from adop_testbed.types import SyntheticTask

HELP_TEXT = """\
Type an instruction and press Enter to have the live model act on it.

Commands:
  :poisoned   tag the NEXT instruction as scenario "poisoned" in the log
              (default is "clean")
  :help       show this message again
  :quit       end the session (or press Ctrl-D / Ctrl-C)
"""


async def run_interactive_session(model: str | None = None, do_reset: bool = True) -> None:
    if do_reset:
        reset_testbed()

    session_id = f"interactive-{datetime.date.today().isoformat()}-{uuid.uuid4().hex[:6]}"
    session_dir = PROJECT_ROOT / "corpus" / f"interactive-session-{session_id}"
    sequencer = SessionSequencer()
    clean_logger = AuditLogger(session_dir / "clean.jsonl", session_id=session_id, sequencer=sequencer)
    poisoned_logger = AuditLogger(session_dir / "poisoned.jsonl", session_id=session_id, sequencer=sequencer)
    await clean_logger.init()
    await poisoned_logger.init()

    print(f"Interactive session {session_id} -- model: {model or DEFAULT_MODEL}")
    print(
        "This is a live demo mode, not the graded benchmark: every call is still logged "
        "and pinned MCP servers are still used, but ad hoc instructions have no fixed "
        "ground truth. Use `live_mode` / `generate_corpus` for the reproducible task set.\n"
    )
    print(HELP_TEXT)

    async with OllamaLiveAgentHost({"clean": clean_logger, "poisoned": poisoned_logger}, model=model) as host:
        scenario_tag = "clean"
        counter = 0
        while True:
            try:
                line = input(f"[{scenario_tag}] adop> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not line:
                continue
            if line in (":quit", ":exit"):
                break
            if line == ":help":
                print(HELP_TEXT)
                continue
            if line == ":poisoned":
                scenario_tag = "poisoned"
                print("Next instruction will be tagged 'poisoned' in the log.")
                continue

            counter += 1
            task = SyntheticTask(
                id=f"interactive-{counter}",
                scenario_tag=scenario_tag,  # type: ignore[arg-type]
                category="issue_triage",
                title=line[:60],
                description="Ad hoc instruction entered live via interactive_mode.",
                instruction=line,
            )
            try:
                summary = await host.run_task_live(task)
            except RuntimeError as exc:
                summary = f"(error) {exc}"
            print(summary.strip() or "(no summary text returned)")
            print()
            scenario_tag = "clean"  # :poisoned only applies to the next instruction

    print(f"Wrote {clean_logger.out_file.relative_to(PROJECT_ROOT)} ({clean_logger.count} records)")
    print(f"Wrote {poisoned_logger.out_file.relative_to(PROJECT_ROOT)} ({poisoned_logger.count} records)")
    print(
        "\ntestbed-repo/ was left as the model modified it -- run "
        "`python -m adop_testbed.scripts.reset_testbed` before your next session "
        "if you want a clean baseline again."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default=None, help=f"Ollama model to use (default: ${{ADOP_OLLAMA_MODEL}} or {DEFAULT_MODEL!r})")
    parser.add_argument(
        "--no-reset", action="store_true",
        help="Skip resetting testbed-repo/ to baseline before the session (default: reset first, like live_mode).",
    )
    args = parser.parse_args()
    asyncio.run(run_interactive_session(model=args.model, do_reset=not args.no_reset))


if __name__ == "__main__":
    main()
