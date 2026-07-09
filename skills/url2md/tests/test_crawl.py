import sys
from pathlib import Path
from unittest.mock import patch

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
