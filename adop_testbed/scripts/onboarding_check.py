#!/usr/bin/env python3
"""Section G.4 onboarding check: verifies a team's environment can run the
testbed before they start, and prints a short orientation summary. Not
graded; just a fast local sanity check.

Run with: python -m adop_testbed.scripts.onboarding_check
"""

from __future__ import annotations

import shutil
import sys

from adop_testbed import __version__
from adop_testbed.sandbox import MOCK_WEB_ROOT, PROJECT_ROOT, REPO_ROOT

CHECKS: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((label, ok, detail))


def main() -> int:
    check("Python >= 3.11", sys.version_info >= (3, 11), f"found {sys.version.split()[0]}")
    check("git executable on PATH", shutil.which("git") is not None)
    check("Synthetic repository present", REPO_ROOT.exists() and (REPO_ROOT / ".git").exists())
    check("Sandboxed mock web present", MOCK_WEB_ROOT.exists() and any(MOCK_WEB_ROOT.glob("*.md")))
    check("docs/LOG_SCHEMA.md present", (PROJECT_ROOT / "docs" / "LOG_SCHEMA.md").exists())
    check("docs/TRUST_ASSUMPTIONS.md present", (PROJECT_ROOT / "docs" / "TRUST_ASSUMPTIONS.md").exists())
    check(
        "Frozen corpus present (corpus/clean, corpus/poisoned)",
        (PROJECT_ROOT / "corpus" / "clean").exists() and (PROJECT_ROOT / "corpus" / "poisoned").exists(),
    )

    try:
        import mcp  # noqa: F401

        check("MCP SDK importable", True)
    except ImportError as exc:
        check("MCP SDK importable", False, str(exc))

    print(f"ADOP testbed onboarding check (adop_testbed {__version__})\n")
    all_ok = True
    for label, ok, detail in CHECKS:
        status = "OK  " if ok else "FAIL"
        print(f"[{status}] {label}" + (f" -- {detail}" if detail else ""))
        all_ok = all_ok and ok

    print()
    if all_ok:
        print("Environment looks ready. Start with README.md, then docs/LOG_SCHEMA.md and docs/TRUST_ASSUMPTIONS.md.")
        return 0
    print("Some checks failed -- see README.md 'Installation' for setup steps.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
