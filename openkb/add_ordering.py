"""Link-based reordering of the ``add`` directory processing queue.

When a document links to another in-scope document, the linked document is
pulled forward in the queue to be processed right after the linking one,
instead of staying at its original (alphabetical) position. Link detection
runs on the already-converted Markdown text (see ``ConvertResult.markdown_text``
in ``converter.py``), so it works uniformly across every source format
``convert_document`` supports, without any per-format special-casing here.
"""

from __future__ import annotations

import re
from pathlib import Path

# Matches [text](target) but not image syntax ![text](target).
_LOCAL_LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")


def _split_link_target(raw: str) -> str:
    """Extract the path portion, stripping an angle-bracket wrapper or a title."""
    raw = raw.strip()
    if raw.startswith("<"):
        end = raw.find(">")
        return raw[1:end] if end != -1 else raw[1:]
    return raw.split(None, 1)[0] if raw else raw


def _is_local_target(target: str) -> bool:
    if not target or target.startswith("#"):
        return False
    return not target.lower().startswith(("http://", "https://", "mailto:", "data:"))


def extract_local_document_links(
    markdown_text: str, source_dir: Path, candidate_paths: set[Path]
) -> list[Path]:
    """Return in-scope local link targets in ``markdown_text``, in first-occurrence order.

    Only links resolving to a path already present in ``candidate_paths`` (the
    full root+subdirectory file listing collected at the start of the ``add``
    run) are returned; web links, anchors, and out-of-scope paths are ignored.
    """
    seen: set[Path] = set()
    ordered: list[Path] = []
    for match in _LOCAL_LINK_RE.finditer(markdown_text):
        target = _split_link_target(match.group(1))
        if not _is_local_target(target):
            continue
        target = target.split("#", 1)[0].strip()
        if not target:
            continue
        try:
            resolved = (source_dir / target).resolve()
        except OSError:
            continue
        if resolved in seen or resolved not in candidate_paths:
            continue
        seen.add(resolved)
        ordered.append(resolved)
    return ordered


def reorder_queue(
    queue: list[Path],
    current_index: int,
    linked_paths: list[Path],
    already_handled: set[Path],
) -> None:
    """Splice not-yet-processed ``linked_paths`` in right after ``current_index``.

    Preserves link-appearance order. A path at or before ``current_index`` is
    already processed (or is the current document itself) and is left alone;
    a path already in ``already_handled`` was moved once already and is not
    rescheduled if another later document links to it again.
    """
    inserted = 0
    for linked_path in linked_paths:
        if linked_path in already_handled:
            continue
        try:
            pos = queue.index(linked_path)
        except ValueError:
            continue
        if pos <= current_index:
            continue
        queue.pop(pos)
        queue.insert(current_index + 1 + inserted, linked_path)
        already_handled.add(linked_path)
        inserted += 1
