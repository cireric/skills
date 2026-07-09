from lib.utils import sanitize_filename, exponential_backoff, load_state, save_state


class TestSanitizeFilename:
    def test_normal(self):
        assert sanitize_filename("hello world") == "hello_world"

    def test_invalid_chars(self):
        assert sanitize_filename('file<>:"/\\|?*name') == "filename"

    def test_empty(self):
        assert sanitize_filename("") == "untitled"

    def test_whitespace_only(self):
        assert sanitize_filename("   ") == "untitled"

    def test_long_filename(self):
        result = sanitize_filename("a" * 300)
        assert len(result) == 200

    def test_none_like_empty(self):
        assert sanitize_filename(None) == "untitled"


class TestExponentialBackoff:
    def test_first_attempt(self):
        wait = exponential_backoff(0)
        assert 1.0 <= wait <= 2.0

    def test_increases(self):
        w0 = exponential_backoff(0, base=1.0)
        w2 = exponential_backoff(2, base=1.0)
        assert w2 > w0

    def test_capped(self):
        wait = exponential_backoff(100, max_wait=10.0)
        assert wait <= 11.0


class TestLoadSaveState:
    def test_load_missing(self, tmp_path):
        assert load_state(str(tmp_path / "nonexistent.json")) is None

    def test_roundtrip(self, tmp_path):
        path = str(tmp_path / "state.json")
        save_state(path, {"urls": ["a", "b"]})
        result = load_state(path)
        assert result is not None
        assert result["urls"] == ["a", "b"]
        assert "last_update" in result

    def test_corrupt_file(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("not json", encoding="utf-8")
        assert load_state(str(path)) is None
