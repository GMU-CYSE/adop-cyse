"""Resets the synthetic repository and the Memory server's persistent store
back to the frozen baseline. Used before (re)generating the corpus and by
the test suite, so runs stay reproducible no matter how many times a task
that writes, commits, or fetches has been executed before.
"""

from __future__ import annotations

import subprocess

from adop_testbed.sandbox import MEMORY_STORE_PATH, PROJECT_ROOT, REPO_ROOT
from adop_testbed.scripts.seed_testbed_repo import seed_if_needed


def reset_testbed() -> None:
    seed_if_needed()  # rebuilds testbed-repo/.git from tracked files on a fresh clone
    subprocess.run(["git", "reset", "--hard", "baseline"], cwd=str(REPO_ROOT), check=True, capture_output=True)
    subprocess.run(["git", "clean", "-fd"], cwd=str(REPO_ROOT), check=True, capture_output=True)
    if MEMORY_STORE_PATH.exists():
        MEMORY_STORE_PATH.unlink()
    exfiltrated = PROJECT_ROOT / "data" / "exfiltrated-diff.txt"
    if exfiltrated.exists():
        exfiltrated.unlink()


if __name__ == "__main__":
    reset_testbed()
    print("Testbed reset to baseline.")
