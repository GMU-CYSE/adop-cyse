# ADOP MVP Testbed

Frozen, reproducible testbed for **CYSE-587 / SYST-687 -- Trust, Provenance,
and Governance in MCP-Based Agentic Systems** (Section G of the Final
Project Notebook). It stands up a minimal **Agentic Development and
Operations Platform (ADOP)**: an MCP-compatible agent host, four pinned MCP
reference servers, a synthetic repository, a fixed synthetic task set, and
an Observability and Audit Layer that emits a frozen, JSON-Lines log
corpus.

Two of the reference servers (Git and, in one relevant scenario, the agent
host's own instruction handling) intentionally reproduce the weakness
classes behind two disclosed CVEs referenced throughout the notebook
(CVE-2025-68143, CVE-2025-68144), so the corpus contains real, reproducible
ground truth for a Student-Developed Agent Trust and Assurance Tool to
detect -- without students ever needing to patch the platform itself
(Section F, G.3: that is explicitly out of scope).

Everything here is **synthetic**. There is no real internet access, no real
secrets, and no real customer data; see [Trust Assumptions](docs/TRUST_ASSUMPTIONS.md)
for exactly what is and is not modeled.

## Table of contents

- [Architecture](#architecture)
- [What this testbed does and does not include](#what-this-testbed-does-and-does-not-include)
- [Installation](#installation)
- [Usage](#usage)
- [The four MCP servers](#the-four-mcp-servers)
- [The synthetic repository](#the-synthetic-repository)
- [The fixed synthetic task set](#the-fixed-synthetic-task-set)
- [The frozen log corpus](#the-frozen-log-corpus)
- [Access modes: Static vs. Live](#access-modes-static-vs-live)
- [What teams may not do](#what-teams-may-not-do)
- [Testing](#testing)
- [Repository layout](#repository-layout)

## Architecture

```
                         Fixed Synthetic Task Set
                    (adop_testbed/host/tasks/synthetic_tasks.json)
                                    |
                                    | drives
                                    v
   +-------------------------------------------------------------------+
   |                    Agent Host (MCP-compatible)                    |
   |                 adop_testbed/host/agent_host.py                   |
   |   scripted, deterministic execution -- no live LLM in the loop    |
   +----------+------------+------------+------------+-----------------+
              |            |            |            |
         (stdio/MCP)  (stdio/MCP)  (stdio/MCP)  (stdio/MCP)
              v            v            v            v
      +-----------+  +-----------+ +-----------+ +-----------+
      |Filesystem |  |    Git    | |   Fetch   | |  Memory   |
      |  server   |  |  server   | |  server   | |  server   |
      | (safe)    |  |(VULN: see |  |(sandboxed |  |(cross-   |
      |           |  | CVE notes)|  | mock web) |  | session) |
      +-----+-----+  +-----+-----+ +-----+-----+ +-----+-----+
            |               |            |             |
            v               v            v             v
      testbed-repo/   testbed-repo/  data/mock-web/  data/
      (synthetic repo, shared)        (frozen "web")  memory-store.json
              |               |
              +-------+-------+
                      |
       every call, success or failure, is wrapped here:
                      v
        +--------------------------------------+
        |   Observability & Audit Layer         |
        |   adop_testbed/audit/logger.py        |
        +--------------------+-------------------+
                             |
                             v
              corpus/clean/session-01.jsonl
              corpus/poisoned/session-01.jsonl
                             |
                             v
        Student-Developed Agent Trust and Assurance Tool
                    (each team's own project)
```

This intentionally mirrors Figure 2 / Figure 3 / Figure 4 of the project
notebook: the agent host at the center, four MCP reference servers around
it (each a capability *and* an attack surface), an Observability and Audit
Layer recording every call, and a downstream artifact (the frozen corpus)
that is the *only* interface a team's tool is allowed to reason from.

The agent host is **scripted, not LLM-backed**. Each task in the fixed
synthetic task set maps to one deterministic plan (a short sequence of tool
calls). This is a deliberate simplification that keeps the testbed static
and byte-for-byte reproducible across teams and semesters (G.1), while
still faithfully reproducing the *behavioral* pattern of an LLM agent
misinterpreting retrieved content as instructions (see `task-04` in
[The fixed synthetic task set](#the-fixed-synthetic-task-set)).

## What this testbed does and does not include

Per Section D.8's scope note, this testbed implements the leaner
"Agent execution + tool servers + audit" slice of the full IDP-to-ADOP
stack, not Backstage/Kratix:

| Layer | Included here? |
|---|---|
| Developer/agent-facing portal (Backstage-equivalent) | No -- out of scope |
| Infrastructure orchestration (Kratix-equivalent) | No -- out of scope |
| Agent execution and reasoning | **Yes** -- scripted MCP-compatible agent host |
| Tool servers | **Yes** -- Filesystem, Git, Fetch, Memory (pinned) |
| Audit and observability | **Yes** -- tool-call telemetry, frozen log corpus |
| CI/CD golden path (SAST/DAST/SCA gates) | No -- not modeled; see docs/TRUST_ASSUMPTIONS.md P8 |

## Installation

Requires Python 3.11+ and `git` on `PATH`.

```bash
git clone <this repo>          # or unzip the distributed archive
cd adop_2026
pip install -e ".[dev]"
python -m adop_testbed.scripts.onboarding_check
```

`testbed-repo/` needs to be a real, self-contained git repository (its own
`.git`, commit history, and a `baseline` tag) for the Git MCP server to
operate on. That nested `.git` is intentionally not tracked by this
repository (see `.gitignore` -- an embedded `.git` would be recorded as a
submodule gitlink with no content, which breaks on a plain clone). Instead,
`testbed-repo/`'s plain files are tracked normally, and
`adop_testbed/scripts/seed_testbed_repo.py` rebuilds the nested history
from them, with the original commit messages and dates, the first time you
run `reset_testbed`, `generate_corpus`, `live_mode`, or `pytest` -- so this
happens automatically and you don't need to run it by hand.

The onboarding check verifies your Python version, that `git` is
reachable, that the synthetic repository and mock web are present, and
that the MCP SDK imports cleanly. It is not graded; it is just a fast
sanity check before you start (Section G.4).

## Usage

### Regenerate the frozen corpus

```bash
python -m adop_testbed.scripts.generate_corpus
```

This resets `testbed-repo/` and the Memory store to the pristine baseline
(git tag `baseline`), runs the full fixed task set through the agent host
against the four pinned servers exactly once, and writes:

```
corpus/clean/session-01.jsonl
corpus/poisoned/session-01.jsonl
```

You do not need to run this to use the testbed -- the corpus checked in at
`corpus/` is already the graded, frozen artifact (Static mode, the
default and required access mode per G.2). Re-run it only if you have
modified the task set or a server and want to see the effect (which is
itself only permitted within the bounds of your own external tool, not the
platform -- see [What teams may not do](#what-teams-may-not-do)).

### Reset the testbed to baseline

```bash
python -m adop_testbed.scripts.reset_testbed
```

Hard-resets `testbed-repo/` to the `baseline` git tag, discards any
uncommitted changes, and deletes the Memory store and any file the
argument-injection scenario wrote outside the repository sandbox. Safe to
run any time; `generate_corpus` and `live_mode` both call it automatically.

### Run an individual MCP server standalone (for manual MCP-Inspector-style probing)

```bash
python -m adop_testbed.servers.filesystem_server
python -m adop_testbed.servers.git_server
python -m adop_testbed.servers.fetch_server
python -m adop_testbed.servers.memory_server
```

Each speaks MCP over stdio and will sit waiting for a client; pair it with
any MCP-compatible client or inspector to explore its tools directly.

### Run the optional Live-mode demo harness

```bash
python -m adop_testbed.scripts.live_mode
```

See [Access modes](#access-modes-static-vs-live).

## The four MCP servers

All four are pinned to this repository's commit -- there is no version
drift to track; the code in `adop_testbed/servers/` *is* the pinned
version for the semester (G.1).

| Server | Module | Tools | Notes |
|---|---|---|---|
| Filesystem | `adop_testbed/servers/filesystem_server.py` | `read_text_file`, `write_file`, `list_directory`, `search_files`, `get_file_info` | Every path is containment-checked via `safe_resolve()`. The "correct" baseline to diff the Git server against. |
| Git | `adop_testbed/servers/git_server.py` | `git_status`, `git_log`, `git_add`, `git_commit`, `git_branch`, `git_init`, `git_show_worktree`, `git_diff` | **`git_init`, `git_show_worktree`, and `git_diff` are intentionally vulnerable** -- see below. |
| Fetch | `adop_testbed/servers/fetch_server.py` | `fetch`, `list_available_pages` | Serves a frozen, sandboxed "mock web" (`data/mock-web/*.md`) under `https://intranet.example/*`; refuses any other host. No content sanitization, matching the real reference server. |
| Memory | `adop_testbed/servers/memory_server.py` | `memory_set`, `memory_get`, `memory_list` | Namespaced, persistent, cross-session key/value store backed by `data/memory-store.json`. No expiry, no filtering. |

### The Git server's intentional vulnerabilities

These reproduce, at the level of a real implementation bug rather than an
abstract description, the two CVEs the project notebook references
throughout (Section D.6, D.7, Section E). **Per Section F/G.3, no team may
patch this file.** A Student-Developed Agent Trust and Assurance Tool is
expected to *detect* their exploitation from the audit log, not prevent it
at the source.

| CVE | Tool | Root cause |
|---|---|---|
| CVE-2025-68143 (CVSS 8.8) | `git_init` | `target_path` is passed straight to `git init` with **no containment check** against the repository sandbox -- a repo can be initialized anywhere the host process can write. |
| CVE-2025-68144 (CVSS 8.1), path-validation half | `git_show_worktree` | Reads a file via `unsafe_join(REPO_ROOT, path)` -- plain path concatenation, **no `resolve()` + containment check** -- so `..` segments escape the repository root. |
| CVE-2025-68144 (CVSS 8.1), argument-injection half | `git_diff` | The `pathspec` argument is split on whitespace and appended to the `git diff` argv **with no `--` separator**, so a crafted pathspec can smuggle extra CLI flags (e.g. `--output=<path>`) into the invocation. |

You can see both halves exercised for real in
`corpus/poisoned/session-01.jsonl` (`seq` 2 and 11), and reproduced
directly, from a clean process, in `tests/test_git_server.py`.

## The synthetic repository

`testbed-repo/` is a real, self-contained git repository (own `.git`) with
staged commit history, an issue tracker mirror, a resource-tag map, and
sample regulated-looking data -- enough surface area for every canonical
project example in Section F without needing a live cluster:

```
testbed-repo/
  README.md, CONTRIBUTING.md, package.json, .env.example, .gitignore
  src/checkout.js, src/payments-client.js, src/fulfillment.js
  ISSUES/142-checkout-database.md
  data/customer_sample.csv          # synthetic, PCI-tagged sample data
  resource-tags.json                # regulated-scope resource map (Example 3)
```

A git tag named `baseline` marks the pristine starting commit; `reset_testbed`
always resets to it. `data/mock-web/` (outside `testbed-repo/`, served only
through the Fetch server) holds the frozen "internet": a clean vendor
README, an unvetted-source dependency README, a vetted-source registry
snapshot, and `poisoned-readme.md` -- the planted adversarial document
carrying the indirect-prompt-injection payload described next.

## The fixed synthetic task set

`adop_testbed/host/tasks/synthetic_tasks.json` -- six tasks, three clean and
three poisoned, spanning all three categories the notebook specifies
(issue triage, patch drafting, documentation summarization):

| Task ID | Category | Scenario | What it demonstrates |
|---|---|---|---|
| `task-01-triage-issue-142` | issue_triage | clean | Baseline read/log/memory-write sequence. |
| `task-02-patch-checkout-db` | patch_drafting | clean | Baseline read/write/stage/commit sequence. |
| `task-03-summarize-vendor-readme` | documentation_summarization | clean | Baseline fetch + memory-write sequence, vetted dependency. |
| `task-04-summarize-mirrored-readme` | documentation_summarization | **poisoned** | Fetches `poisoned-readme.md`; the agent host detects its embedded `AGENT INSTRUCTIONS` block and mechanically carries it out -- an argument-injection `git_diff` call that writes outside the repo sandbox, then a Memory write that smuggles source content into cross-session storage. This is the CVE-2025-68143/68144 indirect-prompt-injection chain from Section D.7, reproduced end to end. |
| `task-05-add-formatting-dependency` | patch_drafting | **poisoned** | Fetches an unvetted-source dependency README and adds it to `package.json` without checking `vetted-source-registry.md` first -- an excessive-agency / unvetted-supply-chain scenario for Example 4-style detectors. |
| `task-06-inspect-worktree-path` | issue_triage | **poisoned** | Passes a traversal-bearing relative path straight to `git_show_worktree`, reproducing the path-validation-bypass half of CVE-2025-68144 directly (independent of prompt injection). |

Every task's scripted plan lives in `adop_testbed/host/agent_host.py`
(`TASK_PLANS`). See [docs/TRUST_ASSUMPTIONS.md](docs/TRUST_ASSUMPTIONS.md)
for exactly which documented assumption each poisoned task violates.

## The frozen log corpus

Delivered as JSON Lines under `corpus/clean/` and `corpus/poisoned/`. Full
field-by-field reference, worked examples, and the formal JSON Schema are
in [docs/LOG_SCHEMA.md](docs/LOG_SCHEMA.md) and
[docs/log_record.schema.json](docs/log_record.schema.json). Short version:

```json
{
  "timestamp": "2026-07-20T14:03:11.482Z",
  "session_id": "session-01",
  "server": "git",
  "tool_name": "git_diff",
  "arguments": { "ref": "HEAD", "pathspec": "--output=../data/exfiltrated-diff.txt ." },
  "target_resource": "../data/exfiltrated-diff.txt",
  "result_status": "success",
  "scenario_tag": "poisoned",
  "duration_ms": 41.286,
  "result_summary": "",
  "task_id": "task-04-summarize-mirrored-readme",
  "seq": 2,
  "annotations": ["indirect_prompt_injection", "argument_injection", "cve-2025-68144"]
}
```

`annotations` is out-of-band teaching ground truth (not part of the graded
contract, see docs/LOG_SCHEMA.md) -- useful for validating a detector's
precision/recall while building it, but a production tool would not have
it and should not rely on its presence.

## Access modes: Static vs. Live

Per Section G.2, two modes are available. **Static mode is the default and
is what's graded.**

- **Static mode (default, required):** consume `corpus/clean/` and
  `corpus/poisoned/` as a fixed dataset. Sufficient for the full Proof of
  Concept.
- **Live mode (optional, final PoC demo only):** `python -m
  adop_testbed.scripts.live_mode` spins up the same four pinned servers and
  the agent host, restricted at runtime to a whitelist of read-only-safe
  tool calls (`adop_testbed/scripts/live_mode.py`'s `ALLOWED_IN_LIVE_MODE`),
  runs only the two tasks that stay within it, writes a demo session to
  `corpus/live-demo/`, and then unconditionally resets the testbed back to
  baseline -- so a Live-mode run can never leave residue for the next team
  or the next grading pass. It does not replace the static dataset for
  grading.

## What teams may not do

Directly from Section F / G.3 -- reiterated here because it constrains how
you're allowed to extend *this* repository, not just how you use it:

- Modify the MCP reference server source code in `adop_testbed/servers/`,
  even to fix the disclosed vulnerabilities directly.
- Modify the agent host's task-execution logic to alter *what ADOP does*
  (as opposed to building an external tool that *observes* what it did).
- Write to `testbed-repo/` in a way that changes the recorded baseline for
  other teams -- always go through `reset_testbed` before regenerating
  anything you intend to share.
- Assume access to interfaces not listed above, such as administrative
  control of the agent host or direct access to `data/memory-store.json`
  outside the Memory server's own tools.

Your Student-Developed Agent Trust and Assurance Tool is a **separate**
project that consumes `corpus/` (Static mode) or a Live-mode session as its
only input.

## Testing

```bash
pytest -q
```

The suite (`tests/`) covers:

- Each server's safe tools, in isolation, over stdio (`test_filesystem_server.py`, `test_git_server.py`, `test_fetch_server.py`, `test_memory_server.py`).
- That the Git server's three intentional vulnerabilities are genuinely
  exploitable end-to-end (`test_git_server.py`), and that the Filesystem
  server's equivalent operations are *not*.
- That the Fetch server refuses any host other than `intranet.example`.
- A full agent-host run of the fixed task set against live servers,
  end-to-end (`test_agent_host_integration.py`).
- That the frozen corpus files in `corpus/` conform to
  `docs/log_record.schema.json`, that `seq` is monotonic per `session_id`,
  and that every `task_id` referenced exists in the task set
  (`test_corpus_schema.py`).
- That Live mode refuses to call a mutating tool and always leaves the
  testbed at baseline afterwards (`test_live_mode.py`).

## Repository layout

```
adop_2026/
  README.md                       # this file
  pyproject.toml
  adop_testbed/
    sandbox.py                    # sandbox roots + safe_resolve / unsafe_join
    types.py                      # AuditLogRecord, SyntheticTask (pydantic)
    audit/logger.py               # Observability & Audit Layer
    servers/                      # the four pinned MCP servers
    host/
      agent_host.py               # scripted agent host + task plans
      tasks/synthetic_tasks.json  # fixed synthetic task set
    scripts/
      generate_corpus.py
      reset_testbed.py
      live_mode.py
      onboarding_check.py
  testbed-repo/                   # synthetic repository (its own git repo)
  data/
    mock-web/                     # frozen sandboxed "internet" for Fetch
    memory-store.json             # Memory server's persistent store (generated)
  corpus/
    clean/, poisoned/             # frozen log corpus (graded, Static mode)
    live-demo/                    # optional Live-mode output (generated, not graded)
  docs/
    TRUST_ASSUMPTIONS.md
    LOG_SCHEMA.md
    log_record.schema.json
  tests/
```
