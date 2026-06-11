from scripts.lib.utils import ensure_dir, normalize_url, read_json, write_json


class TestNormalizeUrl:
    def test_strips_trailing_slash(self):
        assert normalize_url("https://example.com/foo/") == "https://example.com/foo"

    def test_lowercases_domain(self):
        assert normalize_url("HTTPS://Example.COM/Foo") == "https://example.com/foo"

    def test_preserves_query_string(self):
        assert normalize_url("https://example.com/p?a=1") == "https://example.com/p?a=1"

    def test_returns_root_for_empty_path(self):
        assert normalize_url("https://EXAMPLE.COM") == "https://example.com/"

    def test_drops_fragment(self):
        assert normalize_url("https://example.com/p#ref") == "https://example.com/p"


class TestReadWriteJson:
    def test_roundtrip(self, tmp_path):
        data = {"key": "value", "num": 42}
        path = tmp_path / "test.json"
        write_json(data, path)
        assert read_json(path) == data

    def test_read_missing_file(self, tmp_path):
        import pytest

        with pytest.raises(FileNotFoundError):
            read_json(tmp_path / "nope.json")


class TestEnsureDir:
    def test_creates_directory(self, tmp_path):
        d = tmp_path / "a" / "b" / "c"
        result = ensure_dir(d)
        assert result == d
        assert d.exists()

    def test_noop_on_existing(self, tmp_path):
        result = ensure_dir(tmp_path)
        assert result == tmp_path
