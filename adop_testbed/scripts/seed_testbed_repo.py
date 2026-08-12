"""Creates testbed-repo/'s nested git history from the plain files already
checked into the parent repository.

testbed-repo/ is a synthetic repository that needs to be a real, self-
contained git repository (its own .git, with commit history and a
`baseline` tag) so the Git MCP server's tools -- git_status, git_log,
git_diff, etc. -- have something real to operate on. A nested .git
directory is not tracked by the parent repository (see .gitignore:
`testbed-repo/.git/`), because git treats an embedded .git as a submodule
gitlink rather than content, which breaks on a plain clone. Instead, the
parent repository tracks testbed-repo's plain *files*, and this script
rebuilds the nested repository -- with the same commit sequence, messages,
and dates used to originally seed it -- from those files on first use.

`reset_testbed()` calls `seed_if_needed()` automatically, so this normally
runs transparently the first time you use the testbed after a fresh clone.
"""

from __future__ import annotations

import subprocess

from adop_testbed.sandbox import REPO_ROOT

# (files staged together, commit message, author/committer date) -- mirrors
# the exact sequence the testbed was originally authored with.
COMMITS: list[tuple[list[str], str, str]] = [
    (
        ["README.md", "package.json", ".gitignore", ".env.example"],
        "Initial scaffold for checkout-service",
        "2026-06-01T09:00:00",
    ),
    (
        ["src/payments-client.js", "src/checkout.js"],
        "Add checkout total calculation and payment intent creation",
        "2026-06-03T10:15:00",
    ),
    (["src/fulfillment.js"], "Add fulfillment scheduling stub", "2026-06-10T14:30:00"),
    (["CONTRIBUTING.md"], "Document contribution and CI gate requirements", "2026-06-12T08:00:00"),
    (
        ["ISSUES/142-checkout-database.md"],
        "Track issue #142: checkout needs its own database",
        "2026-07-02T11:20:00",
    ),
    (
        ["data/customer_sample.csv", "resource-tags.json"],
        "Add sample regulated customer data and resource tag map",
        "2026-07-15T16:45:00",
    ),
]


def _run(args: list[str], **env_overrides: str) -> None:
    import os

    env = {**os.environ, **env_overrides}
    subprocess.run(["git", *args], cwd=str(REPO_ROOT), check=True, capture_output=True, text=True, env=env)


def seed_if_needed() -> bool:
    """Rebuilds testbed-repo/.git from its tracked plain files if it's missing.

    Returns True if seeding ran, False if a repository already existed.
    """
    if (REPO_ROOT / ".git").exists():
        return False

    _run(["init", "-q"])
    _run(["config", "user.email", "platform-bot@testbed.local"])
    _run(["config", "user.name", "ADOP Testbed Seed"])

    for files, message, date in COMMITS:
        _run(["add", "--", *files])
        _run(["commit", "-q", "-m", message], GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)

    _run(["tag", "-f", "baseline", "HEAD"])
    return True


if __name__ == "__main__":
    seeded = seed_if_needed()
    print("Seeded testbed-repo/ git history." if seeded else "testbed-repo/ already has a git history; left as-is.")
