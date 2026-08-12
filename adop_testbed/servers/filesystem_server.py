#!/usr/bin/env python3
"""Filesystem MCP reference server (pinned, testbed version).

Exposes read/write access to the synthetic repository (testbed-repo/) only.
Every path argument is resolved with `safe_resolve`, which rejects any path
that would escape the repository root. This server is the "correctly
implemented" counterpart to the intentionally vulnerable Git server, so
students have a working baseline to diff their detectors against.

Tools: read_text_file, write_file, list_directory, search_files, get_file_info
"""

from __future__ import annotations

import json
import os

from mcp.server.mcpserver import MCPServer

from adop_testbed.sandbox import REPO_ROOT, safe_resolve

server = MCPServer(name="adop-filesystem-server", version="1.0.0-pinned")


@server.tool()
def read_text_file(path: str) -> str:
    """Read the full contents of a UTF-8 text file inside the synthetic repository.

    Args:
        path: Path relative to the repository root, e.g. 'src/checkout.js'.
    """
    resolved = safe_resolve(REPO_ROOT, path)
    return resolved.read_text(encoding="utf-8")


@server.tool()
def write_file(path: str, content: str) -> str:
    """Write (create or overwrite) a UTF-8 text file inside the synthetic repository.

    Args:
        path: Path relative to the repository root.
        content: Full text content to write.
    """
    resolved = safe_resolve(REPO_ROOT, path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} bytes to {path}"


@server.tool()
def list_directory(path: str = ".") -> str:
    """List the immediate contents of a directory inside the synthetic repository.

    Args:
        path: Directory path relative to the repository root.
    """
    resolved = safe_resolve(REPO_ROOT, path)
    entries = sorted(os.scandir(resolved), key=lambda e: e.name)
    lines = [f"{'[DIR] ' if e.is_dir() else '[FILE]'} {e.name}" for e in entries]
    return "\n".join(lines)


@server.tool()
def search_files(pattern: str, path: str = ".") -> str:
    """Recursively search filenames under the repository root for a substring match.

    Args:
        path: Directory to search under, relative to the repository root.
        pattern: Case-insensitive substring to match against file names.
    """
    start = safe_resolve(REPO_ROOT, path)
    needle = pattern.lower()
    matches: list[str] = []
    for root, dirs, files in os.walk(start):
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in files:
            if needle in name.lower():
                full = os.path.join(root, name)
                matches.append(os.path.relpath(full, REPO_ROOT))
    return "\n".join(matches) if matches else "(no matches)"


@server.tool()
def get_file_info(path: str) -> str:
    """Return size, modification time, and type metadata for a path inside the synthetic repository.

    Args:
        path: Path relative to the repository root.
    """
    resolved = safe_resolve(REPO_ROOT, path)
    st = resolved.stat()
    info = {
        "path": path,
        "size_bytes": st.st_size,
        "modified": st.st_mtime,
        "is_directory": resolved.is_dir(),
        "is_file": resolved.is_file(),
    }
    return json.dumps(info, indent=2)


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
