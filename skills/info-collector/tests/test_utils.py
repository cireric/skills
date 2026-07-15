import json
import builtins

import pytest
from scripts.lib.exceptions import ArtifactError
from scripts.lib.utils import compute_url_hash, ensure_dir, normalize_url, read_json, write_json


class TestNormalizeUrl:
    def test_strips_trailing_slash(self):
        assert normalize_url("https://example.com/foo/") == "https://example.com/foo"

    def test_lowercases_domain(self):
        assert normalize_url("HTTPS://Example.COM/Foo") == "https://example.com/foo"

    def test_preserves_query_string(self):
        assert normalize_url("https://example.com/p?a=1") == "https://example.com/p?a=1"

    def test_strips_www_prefix(self):
        assert normalize_url("https://www.example.com/path") == "https://example.com/path"

    def test_sorts_query_params(self):
        assert normalize_url("https://example.com/path?b=2&a=1") == "https://example.com/path?a=1&b=2"

    def test_www_and_query_combined(self):
        assert normalize_url("https://WWW.Example.COM/path?z=1&a=2") == "https://example.com/path?a=2&z=1"

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
        with pytest.raises(ArtifactError):
            read_json(tmp_path / "nope.json")

    def test_read_json_strips_bom(self, tmp_path):
        data = {"key": "value"}
        path = tmp_path / "bom.json"
        path.write_bytes(b'\xef\xbb\xbf{"key": "value"}')
        assert read_json(path) == data


class TestEnsureDir:
    def test_creates_directory(self, tmp_path):
        d = tmp_path / "a" / "b" / "c"
        result = ensure_dir(d)
        assert result == d
        assert d.exists()

    def test_noop_on_existing(self, tmp_path):
        result = ensure_dir(tmp_path)
        assert result == tmp_path


class TestReadJsonRetry:
    def test_retries_on_oserror(self, monkeypatch, tmp_path):
        path = tmp_path / "test.json"
        data = {"key": "value"}
        json.dump(data, path.open("w"))

        attempts = [0]
        original_open = builtins.open

        def _open(*args, **kwargs):
            attempts[0] += 1
            if attempts[0] == 1:
                raise OSError("Temporary error")
            return original_open(*args, **kwargs)

        monkeypatch.setattr("builtins.open", _open)
        assert read_json(path) == data
        assert attempts[0] == 2

    def test_raises_artifact_error_after_retries(self, monkeypatch, tmp_path):
        path = tmp_path / "test.json"

        def _open(*args, **kwargs):
            raise OSError("Persistent error")

        monkeypatch.setattr("builtins.open", _open)
        with pytest.raises(ArtifactError) as exc_info:
            read_json(path)
        assert "Failed after 3 attempts" in str(exc_info.value)

    def test_json_decode_error_not_retried(self, monkeypatch, tmp_path):
        path = tmp_path / "test.json"
        path.write_text("{}", encoding="utf-8")

        call_count = [0]
        original_load = json.load

        def _load(*args, **kwargs):
            call_count[0] += 1
            raise json.JSONDecodeError("Bad JSON", "", 0)

        monkeypatch.setattr("json.load", _load)
        with pytest.raises(ArtifactError) as exc_info:
            read_json(path)
        assert "Invalid JSON" in str(exc_info.value)
        assert call_count[0] == 1


class TestWriteJsonRetry:
    def test_retries_on_oserror(self, monkeypatch, tmp_path):
        path = tmp_path / "test.json"
        data = {"key": "value"}

        attempts = [0]
        original_open = builtins.open

        def _open(*args, **kwargs):
            attempts[0] += 1
            if attempts[0] == 1:
                raise OSError("Temporary error")
            return original_open(*args, **kwargs)

        monkeypatch.setattr("builtins.open", _open)
        write_json(data, path)
        assert attempts[0] == 2
        assert read_json(path) == data

    def test_raises_artifact_error_after_retries(self, monkeypatch, tmp_path):
        path = tmp_path / "test.json"
        data = {"key": "value"}

        def _open(*args, **kwargs):
            raise OSError("Persistent error")

        monkeypatch.setattr("builtins.open", _open)
        with pytest.raises(ArtifactError) as exc_info:
            write_json(data, path)
        assert "Failed after 3 attempts" in str(exc_info.value)


class TestComputeUrlHash:
    def test_known_hash(self):
        assert compute_url_hash("https://arxiv.org/pdf/2509.16941") == "0991d9ad197a"

    def test_deterministic(self):
        url = "https://example.com/"
        assert compute_url_hash(url) == compute_url_hash(url)

    def test_trailing_slash_normalized(self):
        assert compute_url_hash("https://example.com/") == compute_url_hash("https://example.com")

    def test_www_stripped(self):
        h1 = compute_url_hash("https://www.example.com/path")
        h2 = compute_url_hash("https://example.com/path")
        assert h1 == h2


class TestCJKTokenization:
    def test_cjk_chars_separate_tokens(self):
        from scripts.lib.utils import tokenize_cjk_aware
        tokens = tokenize_cjk_aware("大语言模型", lowercase=True)
        assert tokens == ["大语言模型"]

    def test_cjk_with_latin_mixed(self):
        from scripts.lib.utils import tokenize_cjk_aware
        tokens = tokenize_cjk_aware("AI智能体", lowercase=True)
        assert "ai" in tokens
        assert "智能体" in tokens

    def test_cjk_in_context(self):
        from scripts.lib.utils import tokenize_cjk_aware
        tokens = tokenize_cjk_aware("大 语言 模型 在代码生成中的应用", lowercase=True)
        assert "大语言模型" not in tokens
        assert "大" in tokens or "语言" in tokens

    def test_pure_latin_tokenization(self):
        from scripts.lib.utils import tokenize_cjk_aware
        tokens = tokenize_cjk_aware("Machine learning overview", lowercase=True)
        assert tokens == ["machine", "learning", "overview"]

    def test_lowercase_flag(self):
        from scripts.lib.utils import tokenize_cjk_aware
        tokens = tokenize_cjk_aware("AI智能体", lowercase=False)
        assert "AI" in tokens
        assert "智能体" in tokens

    def test_cjk_full_run(self):
        from scripts.lib.utils import tokenize_cjk_aware
        tokens = tokenize_cjk_aware("深度学习框架PyTorch简介", lowercase=True)
        assert "深度学习框架" in tokens
        assert "pytorch简介" in tokens or "pytorch" in tokens
