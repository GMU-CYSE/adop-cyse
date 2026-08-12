#!/usr/bin/env python3
"""Memory MCP reference server (pinned, testbed version).

Provides a persistent, cross-session key-value store, namespaced by
caller-supplied "namespace" strings (e.g. a project or agent name). Per
Section D.6/D.7, Memory is a durable channel through which poisoned content
can persist beyond a single session: content written into memory during a
poisoned run remains available to a later, otherwise-clean run unless
something notices and clears it. This server does not attempt to detect or
block that; detection is out of scope for the platform itself (Section F).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from mcp.server.mcpserver import MCPServer

from adop_testbed.sandbox import MEMORY_STORE_PATH

server = MCPServer(name="adop-memory-server", version="1.0.0-pinned")


def _load_store() -> dict:
    if not MEMORY_STORE_PATH.exists():
        return {}
    return json.loads(MEMORY_STORE_PATH.read_text(encoding="utf-8"))


def _save_store(store: dict) -> None:
    MEMORY_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_STORE_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")


@server.tool()
def memory_set(namespace: str, key: str, value: str) -> str:
    """Persist a key/value pair in cross-session memory under a namespace.

    Args:
        namespace: Logical grouping for the key, e.g. a project or agent name.
        key: Key to store the value under.
        value: Value to persist.
    """
    store = _load_store()
    store.setdefault(namespace, {})[key] = {
        "value": value,
        "written_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
    }
    _save_store(store)
    return f"stored {namespace}/{key}"


@server.tool()
def memory_get(namespace: str, key: str) -> str:
    """Retrieve a previously stored value by namespace and key.

    Args:
        namespace: Logical grouping the key was stored under.
        key: Key to look up.
    """
    store = _load_store()
    entry = store.get(namespace, {}).get(key)
    if entry is None:
        return f"(no value stored at {namespace}/{key})"
    return entry["value"]


@server.tool()
def memory_list(namespace: str) -> str:
    """List every key stored under a namespace.

    Args:
        namespace: Logical grouping to list keys for.
    """
    store = _load_store()
    keys = list(store.get(namespace, {}).keys())
    return "\n".join(keys) if keys else "(empty)"


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
