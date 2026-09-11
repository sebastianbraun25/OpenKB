"""MCP server exposing taxonomy browsing and tiered search to external clients.

Lets any MCP-capable AI assistant (GitHub Copilot, Claude Code, Cursor, etc.)
browse the wiki's taxonomy and run the tiered BM25 search
(``agent.tools.list_taxonomy_items``/``fulltext_index.TieredWikiSearch``)
without running inside the ``openkb query``/``openkb chat`` agent process or
shelling out to the CLI. Run with the ``openkb-mcp`` console script (stdio
transport), or ``python -m openkb.mcp_server``.

No index cache: both tools rebuild their underlying index fresh on every
call, exactly like the CLI (``openkb list-taxonomy``/``openkb search``) and
the query/chat agent already do (see ``fulltext_index`` module docstring).
This MCP server is typically a longer-lived process than a single CLI
invocation, but OpenKB has no long-running daemon/cache-invalidation concept
today — caching the index across calls here would risk staleness if the KB
changes via a separate ``openkb add`` while this process stays alive, so the
same fresh-per-call rebuild is used deliberately rather than introducing a
new caching model just for this surface.
"""

from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from openkb.agent.tools import list_taxonomy_items
from openkb.config import load_global_config
from openkb.fulltext_index import TieredWikiSearch

mcp = FastMCP("openkb")


def find_kb_dir(start: Path | None = None) -> Path | None:
    """Resolve the active KB root: walk up from *start* (default cwd) looking
    for ``.openkb/``, else fall back to the global config's ``default_kb``.

    Mirrors ``openkb.cli._find_kb_dir``'s resolution order. Kept as a
    separate, lightweight copy here (rather than importing from ``cli.py``)
    so starting this MCP server doesn't pull in ``cli.py``'s much heavier
    import chain (click, litellm, the Agents SDK) just to resolve a
    directory path.
    """
    current = (start or Path.cwd()).resolve()
    while True:
        if (current / ".openkb").is_dir():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent

    gc = load_global_config()
    default = gc.get("default_kb")
    if default:
        candidate = Path(default)
        if (candidate / ".openkb").is_dir():
            return candidate
    return None


def _wiki_root() -> Path:
    """Return the active KB's ``wiki/`` directory, or raise a clear error."""
    kb_dir = find_kb_dir()
    if kb_dir is None:
        raise ValueError(
            "No knowledge base found. Run this from inside a KB directory "
            "(or a subdirectory of one), or set a default with `openkb use <name>`."
        )
    return kb_dir / "wiki"


@mcp.tool()
def list_taxonomy(kind: str | None = None) -> list[dict]:
    """List persisted concept/entity pages with their one-line briefs.

    Semantic browsing, not keyword search: pick the slug(s) that match the
    question's meaning by their brief, then read the full page from
    ``path`` (wiki-root-relative, e.g. ``"concepts/attention.md"``) with a
    filesystem read tool.

    Args:
        kind: Restrict to "concept" or "entity"; omit for both.

    Returns:
        One dict per item: ``kind``, ``slug``, ``path``, ``brief``, and
        ``type`` (entity type, or ``None`` for concepts).
    """
    items = list_taxonomy_items(str(_wiki_root()), kind=kind)
    return [
        {"kind": i.kind, "slug": i.slug, "path": i.path, "brief": i.brief, "type": i.type}
        for i in items
    ]


@mcp.tool()
def search_wiki(query: str, scope: list[str] | None = None, top_k: int = 5) -> dict:
    """Tiered full-text (BM25) search over summaries/sources wiki pages.

    Never covers concepts/entities — use ``list_taxonomy`` for those. Use
    this in addition to, not instead of, taxonomy browsing: a hybrid
    fallback for a specific buried detail (a niche term, an exact figure, an
    author/creation-date only present in a raw source).

    Args:
        query: Free-text search query (keywords or a natural-language question).
        scope: Restrict to a subset of "briefs" (one-line document
            summaries), "summaries" (full document-summary text), "sources"
            (raw source files, including per-page indexing of long
            PageIndex documents); omit to search all three.
        top_k: Maximum ranked results to return per tier.

    Returns:
        ``{tier: [hit, ...]}`` for each searched tier. Each hit has
        ``path``, ``title``, ``score``, ``snippet``, and ``locator``
        (``{"kind": "line"|"page", "value": int}`` or ``None``) — a "page"
        locator names the exact PageIndex page to fetch for that document.
    """
    results = TieredWikiSearch(str(_wiki_root())).search(query, scope=scope, top_k=top_k)
    return {
        tier: [
            {
                "path": hit.path,
                "title": hit.title,
                "score": hit.score,
                "snippet": hit.snippet,
                "locator": (
                    {"kind": hit.locator.kind, "value": hit.locator.value} if hit.locator else None
                ),
            }
            for hit in hits
        ]
        for tier, hits in results.items()
    }


def main() -> None:
    """Entry point for the ``openkb-mcp`` console script (stdio transport)."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
