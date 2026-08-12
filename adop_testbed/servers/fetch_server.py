#!/usr/bin/env python3
"""Fetch MCP reference server (pinned, testbed version).

Retrieves external content for the agent host. For reproducibility (the
testbed must behave identically across teams and semesters -- G.1) this
server does NOT reach the real internet. Instead it serves a small, frozen
"mock web" of pages under data/mock-web/, addressed by a fake
https://intranet.example URL scheme. One page (poisoned-readme.md) is a
planted, adversarial document that carries a hidden instruction payload,
reproducing the "malicious README" indirect-prompt-injection scenario
described in Section D.7 and Section E. This server performs NO
sanitization of fetched content before returning it to the agent host --
exactly like the real Fetch reference server, which returns raw retrieved
text. Any filtering of untrusted content is the agent host's, and in
production, the Student-Developed Agent Trust and Assurance Tool's job.
"""

from __future__ import annotations

from urllib.parse import urlparse

from mcp.server.mcpserver import MCPServer

from adop_testbed.sandbox import MOCK_WEB_ROOT

server = MCPServer(name="adop-fetch-server", version="1.0.0-pinned")


def _url_to_file(url: str):
    parsed = urlparse(url)
    if parsed.hostname != "intranet.example":
        raise ValueError(
            f'Fetch server is pinned to the sandboxed mock web (https://intranet.example/*) '
            f'for this testbed; refusing to reach "{parsed.hostname}".'
        )
    slug = parsed.path.lstrip("/") or "index"
    return MOCK_WEB_ROOT / f"{slug}.md"


@server.tool()
def fetch(url: str) -> str:
    """Retrieve the raw text content of a URL from the sandboxed testbed web.

    Args:
        url: A https://intranet.example/... URL from the testbed's mock web.
    """
    file_path = _url_to_file(url)
    return file_path.read_text(encoding="utf-8")


@server.tool()
def list_available_pages() -> str:
    """List every URL the sandboxed mock web currently serves."""
    urls = [f"https://intranet.example/{p.stem}" for p in sorted(MOCK_WEB_ROOT.glob("*.md"))]
    return "\n".join(urls)


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
