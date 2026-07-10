from __future__ import annotations

import json
from pathlib import Path

from scripts.batch_fetch import _parse_batch_input, _update_collected, _report_pending
from scripts.lib.utils import compute_url_hash


def _make_collected(workdir: Path, entries: list[dict] | None = None) -> Path:
    if entries is None:
        entries = [
            {"url": "https://a.com", "title": "A", "snippet": "sa", "source_tier": 1, "source_file": None, "fetched_content": "", "fetch_failed": False},
            {"url": "https://b.com", "title": "B", "snippet": "sb", "source_tier": 2, "source_file": None, "fetched_content": "", "fetch_failed": False},
        ]
    p = workdir / "collected.json"
    p.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    return p


class TestParseBatchInput:
    def test_array_format(self):
        raw = json.dumps([
            {"url": "https://a.com", "content": "full text A"},
            {"url": "https://b.com", "content": "full text B", "tier": 3},
        ])
        result = _parse_batch_input(raw)
        assert len(result) == 2
        assert result[0]["url"] == "https://a.com"
        assert result[0]["content"] == "full text A"
        assert result[1]["tier"] == 3

    def test_items_format(self):
        raw = json.dumps({"items": [
            {"url": "https://a.com", "content": "text A"},
        ]})
        result = _parse_batch_input(raw)
        assert len(result) == 1
        assert result[0]["url"] == "https://a.com"

    def test_single_object(self):
        raw = json.dumps({"url": "https://a.com", "content": "text A"})
        result = _parse_batch_input(raw)
        assert len(result) == 1

    def test_empty_input(self):
        assert _parse_batch_input("") == []
        assert _parse_batch_input("  ") == []

    def test_missing_url_skipped(self):
        raw = json.dumps([{"content": "text"}])
        result = _parse_batch_input(raw)
        assert len(result) == 0

    def test_missing_content_skipped(self):
        raw = json.dumps([{"url": "https://a.com"}])
        result = _parse_batch_input(raw)
        assert len(result) == 0


class TestUpdateCollected:
    def test_updates_source_file_and_fetched_content(self, tmp_path):
        entries = [
            {"url": "https://a.com", "title": "A", "snippet": "sa", "source_tier": 1, "source_file": None, "fetched_content": "", "fetch_failed": False},
            {"url": "https://b.com", "title": "B", "snippet": "sb", "source_tier": 2, "source_file": None, "fetched_content": "", "fetch_failed": False},
        ]
        p = _make_collected(tmp_path, entries)
        h = compute_url_hash("https://a.com")
        results = [{
            "url": "https://a.com",
            "actual_url": "https://a.com",
            "source_file": f"sources/{h}.md",
            "url_hash": h,
            "char_count": 50000,
            "fetched_content": "First 200 chars of A...",
            "fetch_failed": False,
            "tool_used": "piped",
            "content_insufficient": False,
            "source_tier": 1,
        }]
        _update_collected(entries, results, p)
        updated = json.loads(p.read_text(encoding="utf-8"))
        assert updated[0]["source_file"] == f"sources/{h}.md"
        assert updated[0]["fetched_content"] == "First 200 chars of A..."
        assert updated[0]["fetch_failed"] is False
        assert updated[1]["source_file"] is None

    def test_handles_fetch_failed(self, tmp_path):
        entries = [
            {"url": "https://a.com", "title": "A", "snippet": "sa", "source_tier": 1, "source_file": None, "fetched_content": "", "fetch_failed": False},
        ]
        p = _make_collected(tmp_path, entries)
        results = [{
            "url": "https://a.com",
            "actual_url": "https://a.com",
            "source_file": None,
            "url_hash": "x",
            "char_count": 0,
            "fetched_content": "",
            "fetch_failed": True,
            "tool_used": "",
            "content_insufficient": True,
            "source_tier": None,
        }]
        _update_collected(entries, results, p)
        updated = json.loads(p.read_text(encoding="utf-8"))
        assert updated[0]["fetch_failed"] is True
        assert updated[0]["source_file"] is None


class TestReportPending:
    def test_lists_pending_urls(self, tmp_path, capsys):
        entries = [
            {"url": "https://a.com", "title": "A", "snippet": "sa", "source_tier": 1, "source_file": None, "fetched_content": "", "fetch_failed": False},
            {"url": "https://b.com", "title": "B", "snippet": "sb", "source_tier": 2, "source_file": "sources/existing.md", "fetched_content": "x", "fetch_failed": False},
        ]
        _make_collected(tmp_path, entries)
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()
        (sources_dir / "existing.md").write_text("full text", encoding="utf-8")
        _report_pending(entries, tmp_path)
        captured = capsys.readouterr()
        assert "https://a.com" in captured.out
        assert "Tier 1" in captured.out
        assert "https://b.com" not in captured.out

    def test_no_pending(self, tmp_path, capsys):
        entries = [
            {"url": "https://a.com", "title": "A", "snippet": "sa", "source_tier": 1, "source_file": "sources/a.md", "fetched_content": "x", "fetch_failed": False},
        ]
        _make_collected(tmp_path, entries)
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()
        (sources_dir / "a.md").write_text("full text", encoding="utf-8")
        _report_pending(entries, tmp_path)
        captured = capsys.readouterr()
        assert "No pending" in captured.out


class TestBatchFetchIntegration:
    def test_full_pipeline(self, tmp_path):
        from scripts.batch_fetch import cmd_batch_fetch
        import argparse

        entries = [
            {"url": "https://a.com", "title": "A", "snippet": "sa", "source_tier": 1, "source_file": None, "fetched_content": "", "fetch_failed": False},
            {"url": "https://b.com", "title": "B", "snippet": "sb", "source_tier": 2, "source_file": None, "fetched_content": "", "fetch_failed": False},
        ]
        _make_collected(tmp_path, entries)

        batch_input = json.dumps([
            {"url": "https://a.com", "content": "Full article text for A. " * 100, "tier": 1},
            {"url": "https://b.com", "content": "Full article text for B. " * 100, "tier": 2},
        ])

        args = argparse.Namespace(
            from_stdin=True,
            pending=False,
            workdir=str(tmp_path),
        )

        import io
        old_stdin = __import__("sys").stdin
        __import__("sys").stdin = io.StringIO(batch_input)
        try:
            cmd_batch_fetch(args)
        finally:
            __import__("sys").stdin = old_stdin

        collected = json.loads((tmp_path / "collected.json").read_text(encoding="utf-8"))
        assert collected[0]["source_file"] is not None
        assert collected[0]["source_file"].startswith("sources/")
        assert collected[0]["fetched_content"] != ""
        assert collected[1]["source_file"] is not None
        assert not collected[0]["fetch_failed"]

        a_hash = compute_url_hash("https://a.com")
        a_file = tmp_path / "sources" / f"{a_hash}.md"
        assert a_file.exists()
        assert "Full article text for A" in a_file.read_text(encoding="utf-8")

    def test_pending_flag(self, tmp_path, capsys):
        from scripts.batch_fetch import cmd_batch_fetch
        import argparse

        entries = [
            {"url": "https://a.com", "title": "A", "snippet": "sa", "source_tier": 1, "source_file": None, "fetched_content": "", "fetch_failed": False},
        ]
        _make_collected(tmp_path, entries)

        args = argparse.Namespace(
            from_stdin=False,
            pending=True,
            workdir=str(tmp_path),
        )
        cmd_batch_fetch(args)
        captured = capsys.readouterr()
        assert "https://a.com" in captured.out
