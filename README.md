# ADOP MVP Testbed

**CYSE-587 / SYST-687 — Trust, Provenance, and Governance in MCP-Based Agentic Systems**

This repository is the instructor-provided testbed for the course's final project (Section G of the Project Notebook). It stands up a minimal **Agentic Development and Operations Platform (ADOP)**: an MCP-compatible agent host, four pinned MCP reference servers (Filesystem, Git, Fetch, Memory), a synthetic repository, a fixed synthetic task set, and an Observability and Audit Layer that emits JSON Lines tool-call telemetry.

Two of those servers, and specifically the agent driving them, intentionally reproduce the weakness classes behind two disclosed CVEs (CVE-2025-68143, CVE-2025-68144), so a live run against this testbed is real, reproducible ground truth, not a synthetic exercise.

**This testbed is not itself graded.** What counts is the external **Student-Developed Agent Trust and Assurance Tool** your team builds on top of the logs it produces. Nothing about how well you operate the testbed factors into your grade.

## Start here

This repository has two companion documents. Read them in this order:

| Document | Answers |
|---|---|
| **Project Notebook** (`CYSE_587_Project_Notebook.docx`, Canvas) | What is ADOP, why does it matter, what must my team build, and what are the deliverables? |
| **Guided Lab** (`ADOP_Lab_Guide.md`, this repository) | How do I install this repository, run it, read its files, add my own scenarios, and prove I understand it? |

This README is deliberately short. It tells you what the repository is, how it is organized, and how to get it running. For the *why* (IDP → ADOP, MCP, the autonomy spectrum, the six canonical project examples) see the Notebook. For the *how* (file-by-file walkthrough, task authoring, log schema, troubleshooting, and the lab completion checklist) see the Guided Lab.

## Repository layout

```
adop-cyse/
  README.md                       # this file
  pyproject.toml
  adop_testbed/
    sandbox.py                    # sandbox roots + safe_resolve / unsafe_join
    types.py                      # AuditLogRecord, SyntheticTask (pydantic)
    audit/logger.py               # Observability & Audit Layer
    servers/                      # the four pinned MCP servers
    host/
      agent_host.py               # scripted reference host (deterministic, TASK_PLANS)
      llm_agent_host.py           # Ollama-backed LLM host (primary, live_mode)
      annotate.py                 # generic weakness-class annotation
      tasks/synthetic_tasks.json  # fixed synthetic task set
    scripts/
      live_mode.py                # primary entrypoint
      generate_corpus.py          # produces the reference corpus
      reset_testbed.py
      seed_testbed_repo.py
      onboarding_check.py
  testbed-repo/                   # synthetic repository (its own git repo)
  data/
    mock-web/                     # frozen, sandboxed "internet" for the Fetch server
    memory-store.json             # Memory server's persistent store (generated)
  corpus/
    clean/, poisoned/             # small reference corpus (scripted, checked in)
    live-session-*/               # your own live sessions (generated, gitignored)
  docs/
    TRUST_ASSUMPTIONS.md
    LOG_SCHEMA.md
    log_record.schema.json
  tests/
  ADOP_Lab_Guide.md                # <- start your first day here
```

## Requirements

- Python 3.11+, with `git` on `PATH`.
- [Ollama](https://ollama.com/download), running locally, with a tool-calling-capable model pulled (default: `qwen2.5:7b`; `llama3.1:8b` also works well). See the Guided Lab §4 for model recommendations and pitfalls.

## Installation

```bash
git clone https://github.com/GMU-CYSE/adop-cyse.git
cd adop-cyse
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m adop_testbed.scripts.onboarding_check
```

The onboarding check confirms your Python version, that `git` is reachable, that the synthetic repository and mock web are present, and that the MCP SDK imports cleanly. It does not check Ollama; `live_mode` will tell you clearly if Ollama isn't reachable.

## Running it

```bash
# reset the synthetic repository to its clean baseline
python -m adop_testbed.scripts.reset_testbed

# run the deterministic scripted host (no LLM) to sanity-check the install
python -m adop_testbed.scripts.generate_corpus

# run the full test suite
pytest -q

# run a live session driven by your local model (the primary usage)
python -m adop_testbed.scripts.live_mode
```

Every live session writes structured telemetry to `corpus/live-session-<date>-<id>/{clean,poisoned}.jsonl`. That telemetry, and only that telemetry, is the input your Trust and Assurance Tool is allowed to consume.

For a guided, step-by-step first run, an explanation of every file above, how to author a new task/scenario, the exact log schema, the two intentional Git-server vulnerabilities, and a checklist your team can use as proof of a completed lab session, go to **[`ADOP_Lab_Guide.md`](./ADOP_Lab_Guide.md)**.

## What you may not do

You may not modify the MCP reference server source code in `adop_testbed/servers/`, modify either agent host to change *what ADOP does*, or assume access to interfaces not documented here (Section F/G.3 of the Project Notebook; restated with the reasoning behind it in the Guided Lab §10).

## Support

Questions about the testbed's infrastructure itself (not the tool your team is designing) go to the course support channel referenced in Section G.4 of the Project Notebook. Instructor: Alexandre B. Barreto (adebarro@gmu.edu).
