import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_scripts_dir = str(Path(__file__).resolve().parent.parent / "scripts")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from crawl import _load_config, _find_system_chrome, _preflight_check, _venv_python, _venv_pip


class TestVenvHelpers:
    def test_python_windows(self):
        with patch("crawl.sys") as mock_sys:
            mock_sys.platform = "win32"
            assert _venv_python() == ".venv\\Scripts\\python.exe"

    def test_python_linux(self):
        with patch("crawl.sys") as mock_sys:
            mock_sys.platform = "linux"
            assert _venv_python() == ".venv/bin/python"

    def test_pip_windows(self):
        with patch("crawl.sys") as mock_sys:
            mock_sys.platform = "win32"
            assert _venv_pip() == ".venv\\Scripts\\pip.exe"

    def test_pip_linux(self):
        with patch("crawl.sys") as mock_sys:
            mock_sys.platform = "linux"
            assert _venv_pip() == ".venv/bin/pip"


class TestLoadConfig:
    def test_missing_config(self, tmp_path):
        from crawl import CONFIG_PATH
        with patch("crawl.CONFIG_PATH", tmp_path / "nonexistent.yaml"):
            try:
                _load_config()
                assert False, "Should have raised FileNotFoundError"
            except FileNotFoundError as e:
                assert "Config file not found" in str(e)

    def test_valid_config(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text('output_dir: "test/"\ndelay: 3.0\n', encoding="utf-8")
        with patch("crawl.CONFIG_PATH", config_path):
            config = _load_config()
            assert config["output_dir"] == "test/"
            assert config["delay"] == 3.0


class TestPreflightCheck:
    def test_missing_config(self, tmp_path):
        with patch("crawl.CONFIG_PATH", tmp_path / "nonexistent.yaml"):
            errors = _preflight_check()
            assert any("Config file not found" in e for e in errors)

    def test_missing_chrome(self):
        with patch("crawl._find_system_chrome", return_value=None):
            errors = _preflight_check()
            assert any("Chrome not found" in e for e in errors)


def _make_crawl_result(success, files=None, error=None, count=1):
    from lib.api import CrawlResult
    return CrawlResult(success=success, files=files or [], error=error, article_count=count)


class TestMultiUrlCrawl:
    def test_multiple_urls_crawl_all(self, capsys):
        from crawl import main
        with patch("crawl.sys.argv", ["crawl.py", "https://a.com/1", "https://a.com/2", "--output", "out/"]):
            with patch("crawl._preflight_check", return_value=[]):
                with patch("lib.api.crawl_url", side_effect=[
                    _make_crawl_result(True, ["out/one.md"]),
                    _make_crawl_result(True, ["out/two.md"]),
                ]) as mock_crawl:
                    main()
        assert mock_crawl.call_count == 2
        assert mock_crawl.call_args_list[0].kwargs["url"] == "https://a.com/1"
        assert mock_crawl.call_args_list[1].kwargs["url"] == "https://a.com/2"
        out = capsys.readouterr().out
        assert "已保存到: out/one.md" in out
        assert "已保存到: out/two.md" in out
        assert '"out/one.md"' in out and '"out/two.md"' in out

    def test_partial_failure_keeps_successes(self, capsys):
        from crawl import main
        with patch("crawl.sys.argv", ["crawl.py", "https://a.com/1", "https://a.com/2"]):
            with patch("crawl._preflight_check", return_value=[]):
                with patch("lib.api.crawl_url", side_effect=[
                    _make_crawl_result(False, error="boom"),
                    _make_crawl_result(True, ["out/two.md"]),
                ]):
                    main()
        out = capsys.readouterr().out
        assert "抓取失败: https://a.com/1: boom" in out
        assert "已保存到: out/two.md" in out

    def test_all_fail_exits_nonzero(self, capsys):
        from crawl import main
        with patch("crawl.sys.argv", ["crawl.py", "https://a.com/1", "https://a.com/2"]):
            with patch("crawl._preflight_check", return_value=[]):
                with patch("lib.api.crawl_url", return_value=_make_crawl_result(False, error="boom")):
                    with pytest.raises(SystemExit) as exc:
                        main()
        assert exc.value.code == 1

    def test_filename_rejected_for_multiple_urls(self):
        from crawl import main
        with patch("crawl.sys.argv", ["crawl.py", "https://a.com/1", "https://a.com/2", "--filename", "x.md"]):
            with pytest.raises(SystemExit) as exc:
                main()
        assert exc.value.code == 2


class TestPreflightStandalone:
    def test_preflight_runs_without_url(self, capsys):
        """回归：`--preflight` 必须可独立运行（url 可选）。"""
        from crawl import main
        with patch("crawl.sys.argv", ["crawl.py", "--preflight"]):
            with patch("crawl._preflight_check", return_value=[]):
                main()
        out = capsys.readouterr().out
        assert "PREFLIGHT OK" in out

    def test_no_url_without_preflight_is_usage_error(self):
        from crawl import main
        with patch("crawl.sys.argv", ["crawl.py"]):
            with pytest.raises(SystemExit) as exc:
                main()
        assert exc.value.code == 2
