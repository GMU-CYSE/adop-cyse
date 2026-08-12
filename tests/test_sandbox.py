from __future__ import annotations

import pytest

from adop_testbed.sandbox import REPO_ROOT, PathEscapeError, safe_resolve, unsafe_join


def test_safe_resolve_allows_paths_inside_root():
    resolved = safe_resolve(REPO_ROOT, "src/checkout.js")
    assert resolved == (REPO_ROOT / "src" / "checkout.js").resolve()


def test_safe_resolve_allows_root_itself():
    assert safe_resolve(REPO_ROOT, ".") == REPO_ROOT.resolve()


@pytest.mark.parametrize(
    "escape_path",
    [
        "../secret-outside-sandbox.txt",
        "../../data/secret-outside-sandbox.txt",
        "src/../../data/secret-outside-sandbox.txt",
    ],
)
def test_safe_resolve_rejects_traversal(escape_path: str):
    with pytest.raises(PathEscapeError):
        safe_resolve(REPO_ROOT, escape_path)


def test_unsafe_join_does_not_raise_on_traversal():
    # Documents the deliberately-vulnerable behavior used by git_show_worktree:
    # unsafe_join performs no containment check at all.
    escaped = unsafe_join(REPO_ROOT, "../data/secret-outside-sandbox.txt")
    assert escaped == (REPO_ROOT.parent / "data" / "secret-outside-sandbox.txt")
    assert not str(escaped).startswith(str(REPO_ROOT))
