"""Unit tests for openkb.add_ordering (link-based add-queue reordering)."""

from __future__ import annotations

from pathlib import Path

from openkb.add_ordering import extract_local_document_links, reorder_queue


class TestExtractLocalDocumentLinks:
    def _candidates(self, source_dir: Path, *names: str) -> set[Path]:
        return {(source_dir / name).resolve() for name in names}

    def test_finds_simple_relative_link(self, tmp_path):
        candidates = self._candidates(tmp_path, "b.md")
        links = extract_local_document_links("See [B](b.md) for details.", tmp_path, candidates)
        assert links == [(tmp_path / "b.md").resolve()]

    def test_ignores_image_links(self, tmp_path):
        candidates = self._candidates(tmp_path, "pic.png")
        links = extract_local_document_links("![alt](pic.png)", tmp_path, candidates)
        assert links == []

    def test_ignores_external_and_mailto_links(self, tmp_path):
        candidates = self._candidates(tmp_path, "b.md")
        text = "[web](https://example.com/b.md) [mail](mailto:a@b.com) [B](b.md)"
        links = extract_local_document_links(text, tmp_path, candidates)
        assert links == [(tmp_path / "b.md").resolve()]

    def test_ignores_pure_anchor_links(self, tmp_path):
        candidates = self._candidates(tmp_path, "b.md")
        links = extract_local_document_links("[jump](#section)", tmp_path, candidates)
        assert links == []

    def test_strips_fragment_from_target(self, tmp_path):
        candidates = self._candidates(tmp_path, "b.md")
        links = extract_local_document_links("[B](b.md#section)", tmp_path, candidates)
        assert links == [(tmp_path / "b.md").resolve()]

    def test_ignores_links_outside_candidate_set(self, tmp_path):
        candidates: set[Path] = set()
        links = extract_local_document_links("[B](b.md)", tmp_path, candidates)
        assert links == []

    def test_preserves_first_occurrence_order_and_dedupes(self, tmp_path):
        candidates = self._candidates(tmp_path, "b.md", "c.md")
        text = "[C](c.md) then [B](b.md) then [C again](c.md)"
        links = extract_local_document_links(text, tmp_path, candidates)
        assert links == [(tmp_path / "c.md").resolve(), (tmp_path / "b.md").resolve()]


class TestReorderQueue:
    def test_moves_later_link_right_after_current_index(self, tmp_path):
        a, m, z = tuple((tmp_path / n).resolve() for n in ("a.md", "m.md", "z.md"))
        queue = [a, m, z]
        reorder_queue(queue, current_index=0, linked_paths=[z], already_handled=set())
        assert queue == [a, z, m]

    def test_preserves_link_appearance_order_for_multiple_targets(self, tmp_path):
        a, m, y, z = tuple((tmp_path / n).resolve() for n in ("a.md", "m.md", "y.md", "z.md"))
        queue = [a, m, y, z]
        reorder_queue(queue, current_index=0, linked_paths=[z, y], already_handled=set())
        assert queue == [a, z, y, m]

    def test_leaves_already_processed_targets_untouched(self, tmp_path):
        a, b, c = tuple((tmp_path / n).resolve() for n in ("a.md", "b.md", "c.md"))
        queue = [a, b, c]
        # current_index=1 means a (index 0) already processed — linking back to it is a no-op.
        reorder_queue(queue, current_index=1, linked_paths=[a], already_handled=set())
        assert queue == [a, b, c]

    def test_does_not_reschedule_already_handled_target(self, tmp_path):
        a, m, z = tuple((tmp_path / n).resolve() for n in ("a.md", "m.md", "z.md"))
        queue = [a, m, z]
        already_handled = {z}
        reorder_queue(queue, current_index=0, linked_paths=[z], already_handled=already_handled)
        assert queue == [a, m, z]

    def test_ignores_link_target_not_in_queue(self, tmp_path):
        a, m = tuple((tmp_path / n).resolve() for n in ("a.md", "m.md"))
        missing = (tmp_path / "missing.md").resolve()
        queue = [a, m]
        reorder_queue(queue, current_index=0, linked_paths=[missing], already_handled=set())
        assert queue == [a, m]
