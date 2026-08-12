#!/usr/bin/env python3
"""Git MCP reference server (pinned, testbed version).

This server intentionally reproduces the weakness classes behind the two
disclosed reference-implementation CVEs referenced throughout the project
notebook (Section D.6, D.7, Section E):

  - CVE-2025-68143 (CVSS 8.8): unrestricted `git_init` capability. The
    `git_init` tool does not confine its target directory to the synthetic
    repository sandbox, so it can initialize a git repository at any
    filesystem path the host process can write to.

  - CVE-2025-68144 (CVSS 8.1): path validation bypass AND argument
    injection in git-adjacent tools.
      * `git_show_worktree` reads a working-tree file directly off disk
        using an unsafe path join (no containment check), allowing `..`
        traversal outside the repository root.
      * `git_diff` builds its `git diff` argv by naively splitting a
        caller-supplied `pathspec` string on whitespace, without a `--`
        separator, so a crafted pathspec can inject extra CLI flags (e.g.
        `--output=<path>`) into the invocation.

These are the exact two components highlighted in red in Figure 2 of the
notebook. They exist here on purpose, as fixed, reproducible ground truth
for the Student-Developed Agent Trust and Assurance Tool to detect from the
audit log alone (per Section F, teams may NOT patch this file directly).
"""

from __future__ import annotations

import subprocess

from mcp.server.mcpserver import MCPServer

from adop_testbed.sandbox import REPO_ROOT, safe_resolve, unsafe_join

server = MCPServer(name="adop-git-server", version="1.0.0-pinned")


def _git(args: list[str], cwd: str | None = None) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd or str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"git {' '.join(args)} failed")
    return proc.stdout


# ---------------------------------------------------------------------------
# Safe tools
# ---------------------------------------------------------------------------


@server.tool()
def git_status() -> str:
    """Show the working tree status of the synthetic repository."""
    out = _git(["status", "--porcelain=v1", "-b"])
    return out or "(clean)"


@server.tool()
def git_log(max_count: int = 20) -> str:
    """Show commit history of the synthetic repository.

    Args:
        max_count: Maximum number of commits to return (1-200).
    """
    max_count = max(1, min(max_count, 200))
    return _git(["log", f"-n{max_count}", "--pretty=format:%H|%an|%ad|%s", "--date=iso-strict"])


@server.tool()
def git_add(path: str) -> str:
    """Stage a file inside the synthetic repository for commit.

    Args:
        path: Path relative to the repository root.
    """
    safe_resolve(REPO_ROOT, path)  # containment enforced before touching the index
    out = _git(["add", "--", path])
    return out or f"staged {path}"


@server.tool()
def git_commit(message: str) -> str:
    """Create a commit from the currently staged changes.

    Args:
        message: Commit message.
    """
    return _git(["commit", "-m", message])


@server.tool()
def git_branch() -> str:
    """List local branches of the synthetic repository."""
    return _git(["branch", "--list"])


# ---------------------------------------------------------------------------
# Vulnerable tools (intentional -- see module docstring)
# ---------------------------------------------------------------------------


@server.tool()
def git_init(target_path: str) -> str:
    """Initialize a new git repository at the given target path.

    CVE-2025-68143: `target_path` is NEVER checked against the sandbox
    root before being handed to `git init`.

    Args:
        target_path: Filesystem path where a new repository should be created.
    """
    # VULNERABLE: no safe_resolve(REPO_ROOT, target_path) containment check here.
    return _git(["init", target_path], cwd=".")


@server.tool()
def git_show_worktree(path: str) -> str:
    """Read the current working-tree contents of a tracked file (fast path,
    bypasses git object lookup).

    CVE-2025-68144 (path-validation half): reads worktree files by raw
    file I/O with an unsafe join, so `..` segments in `path` escape
    REPO_ROOT untouched.

    Args:
        path: Path relative to the repository root.
    """
    # VULNERABLE: unsafe_join allows ../ segments to escape REPO_ROOT.
    resolved = unsafe_join(REPO_ROOT, path)
    return resolved.read_text(encoding="utf-8")


@server.tool()
def git_diff(pathspec: str = ".", ref: str = "HEAD") -> str:
    """Show the diff between the working tree and a git ref for the given pathspec.

    CVE-2025-68144 (argument-injection half): `pathspec` is naively
    tokenized into argv with no `--` guard, so a crafted pathspec can
    smuggle extra flags (e.g. "--output=<path>") into the `git diff`
    invocation.

    Args:
        ref: Git ref to diff against.
        pathspec: Path or pathspec to diff. Accepts a raw string.
    """
    # VULNERABLE: naive whitespace split with no leading "--" separator lets a
    # crafted pathspec smuggle extra flags (e.g. "--output=<path>") into argv.
    extra_args = [tok for tok in pathspec.split() if tok]
    out = _git(["diff", ref, *extra_args])
    return out or "(no changes)"


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
