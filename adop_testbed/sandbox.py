"""Filesystem sandbox roots and path-containment helpers shared by every
MCP server in the testbed.

`safe_resolve` is the CORRECTLY implemented containment check, used by the
Filesystem server and by every safe tool on the Git server. The Git server's
`git_show_worktree` and `git_diff` tools deliberately do NOT use it for one
argument each -- see servers/git_server.py -- in order to faithfully
reproduce the path-validation-bypass and argument-injection weakness classes
described in CVE-2025-68143 / CVE-2025-68144 (Section D.6/D.7/E of the
project notebook).
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# The synthetic repository the Filesystem and Git servers operate against.
REPO_ROOT = PROJECT_ROOT / "testbed-repo"

# The local, sandboxed "web" the Fetch server serves content from.
MOCK_WEB_ROOT = PROJECT_ROOT / "data" / "mock-web"

# The Memory server's persistent cross-session store.
MEMORY_STORE_PATH = PROJECT_ROOT / "data" / "memory-store.json"


class PathEscapeError(Exception):
    """Raised when a caller-supplied path would resolve outside its sandbox root."""

    def __init__(self, requested: str) -> None:
        super().__init__(f'Path "{requested}" resolves outside the permitted sandbox root.')
        self.requested = requested


def safe_resolve(root: Path, user_path: str) -> Path:
    """Resolve `user_path` against `root` and RAISE if the result escapes `root`.

    Equivalent to `path.resolve(root, user_path)` plus a containment check
    (compare against `os.path.commonpath`), not a naive `root / user_path`
    join, which would allow `..` segments through untouched.
    """
    root = root.resolve()
    candidate = (root / user_path).resolve()
    try:
        common = os.path.commonpath([str(root), str(candidate)])
    except ValueError:
        # Different drives on Windows, for example -- definitely outside root.
        raise PathEscapeError(user_path) from None
    if common != str(root):
        raise PathEscapeError(user_path)
    return candidate


def unsafe_join(root: Path, user_path: str) -> Path:
    """Deliberately UNSAFE join, kept separate and named loudly so its use
    sites are searchable. Mirrors a real-world implementation bug: building
    a path with plain concatenation instead of resolving + checking
    containment, allowing `..` segments to escape the intended root.
    """
    return Path(os.path.normpath(os.path.join(str(root), user_path)))
