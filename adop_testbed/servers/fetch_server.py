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
            f'This Fetch server only reaches https://intranet.example/*; refusing to reach '
            f'"{parsed.hostname}". Call list_available_pages to see valid URLs.'
        )
    slug = parsed.path.lstrip("/") or "index"
    return MOCK_WEB_ROOT / f"{slug}.md"


@server.tool()
def fetch(url: str) -> str:
    """Retrieve the raw text content of a URL. This Fetch server ONLY reaches
    this organization's internal documentation mirror, at URLs of the exact
    form https://intranet.example/<page-name> -- it cannot reach the real
    internet (github.com, raw.githubusercontent.com, etc. will always fail).
    If you don't already know the exact page name, call list_available_pages
    first instead of guessing a URL.

    Args:
        url: A https://intranet.example/<page-name> URL. Call list_available_pages first if unsure.
    """
    file_path = _url_to_file(url)
    return file_path.read_text(encoding="utf-8")


@server.tool()
def list_available_pages() -> str:
    """List every https://intranet.example/... URL this Fetch server can
    currently retrieve. Call this first whenever you need to fetch internal
    documentation but don't already know the exact page name -- guessing a
    real-world URL will always fail, since this server cannot reach the
    real internet.
    """
    urls = [f"https://intranet.example/{p.stem}" for p in sorted(MOCK_WEB_ROOT.glob("*.md"))]
    return "\n".join(urls)


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
