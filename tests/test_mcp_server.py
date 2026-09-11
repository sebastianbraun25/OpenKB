"""Tests for openkb.mcp_server (MCP tools: list_taxonomy, search_wiki)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from openkb.mcp_server import find_kb_dir, list_taxonomy, search_wiki


def _make_kb(tmp_path):
    """Create a minimal KB (``.openkb/`` marker + a few wiki pages)."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / ".openkb").mkdir()
    (tmp_path / "wiki" / "concepts").mkdir(parents=True)
    (tmp_path / "wiki" / "summaries").mkdir(parents=True)
    (tmp_path / "wiki" / "sources").mkdir(parents=True)
    (tmp_path / "wiki" / "concepts" / "attention.md").write_text(
        '---\ndescription: "How attention works"\n---\n\n# Attention\n\nBody.',
        encoding="utf-8",
    )
    (tmp_path / "wiki" / "summaries" / "doc.md").write_text(
        '---\ndescription: "Overview"\n---\n\n# Doc\n\nDetails about field_xyz appear here.',
        encoding="utf-8",
    )
    return tmp_path


class TestFindKbDir:
    def test_finds_kb_at_cwd(self, tmp_path, monkeypatch):
        _make_kb(tmp_path)
        monkeypatch.chdir(tmp_path)

        assert find_kb_dir() == tmp_path.resolve()

    def test_finds_kb_by_walking_up_from_subdirectory(self, tmp_path, monkeypatch):
        _make_kb(tmp_path)
        subdir = tmp_path / "a" / "b"
        subdir.mkdir(parents=True)
        monkeypatch.chdir(subdir)

        assert find_kb_dir() == tmp_path.resolve()

    def test_falls_back_to_global_default_kb(self, tmp_path, monkeypatch):
        no_kb_cwd = tmp_path / "elsewhere"
        no_kb_cwd.mkdir()
        kb_dir = _make_kb(tmp_path / "the-kb")
        monkeypatch.chdir(no_kb_cwd)

        with patch(
            "openkb.mcp_server.load_global_config",
            return_value={"default_kb": str(kb_dir)},
        ):
            assert find_kb_dir() == kb_dir.resolve()

    def test_returns_none_when_no_kb_found_anywhere(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        with patch("openkb.mcp_server.load_global_config", return_value={}):
            assert find_kb_dir() is None


class TestMcpListTaxonomy:
    def test_lists_items_as_plain_dicts(self, tmp_path, monkeypatch):
        _make_kb(tmp_path)
        monkeypatch.chdir(tmp_path)

        result = list_taxonomy()

        assert result == [
            {
                "kind": "concept",
                "slug": "attention",
                "path": "concepts/attention.md",
                "brief": "How attention works",
                "type": None,
            }
        ]

    def test_no_kb_raises_clear_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        with patch("openkb.mcp_server.load_global_config", return_value={}):
            with pytest.raises(ValueError, match="No knowledge base found"):
                list_taxonomy()


class TestMcpSearchWiki:
    def test_finds_hit_in_summaries_tier(self, tmp_path, monkeypatch):
        _make_kb(tmp_path)
        monkeypatch.chdir(tmp_path)

        result = search_wiki("field_xyz")

        assert result["briefs"] == []
        assert len(result["summaries"]) == 1
        assert result["summaries"][0]["path"] == "summaries/doc.md"
        assert result["summaries"][0]["locator"] == {"kind": "line", "value": 4}
        assert result["sources"] == []

    def test_scope_restricts_tiers(self, tmp_path, monkeypatch):
        _make_kb(tmp_path)
        monkeypatch.chdir(tmp_path)

        result = search_wiki("field_xyz", scope=["briefs"])

        assert set(result.keys()) == {"briefs"}

    def test_invalid_scope_raises(self, tmp_path, monkeypatch):
        _make_kb(tmp_path)
        monkeypatch.chdir(tmp_path)

        with pytest.raises(ValueError, match="Unknown scope"):
            search_wiki("field_xyz", scope=["not-a-tier"])
