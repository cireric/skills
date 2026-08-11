"""Tests for video-download CLI using a fake yt-dlp binary."""
from pathlib import Path


class TestInfo:
    def test_prints_metadata(self, fake_ytdlp):
        result = fake_ytdlp.run(["info", "http://example.com/video"])
        assert result.exitcode == 0
        assert "Fake Test Video" in result.stdout
        assert "fake123" in result.stdout
        assert "720p" in result.stdout

    def test_uses_json_metadata_flag(self, fake_ytdlp):
        fake_ytdlp.run(["info", "http://example.com/video"])
        log = fake_ytdlp.read_log()
        assert "-J" in log[0]
        assert log[0][-1] == "http://example.com/video"


class TestFormats:
    def test_lists_formats(self, fake_ytdlp):
        result = fake_ytdlp.run(["formats", "http://example.com/video"])
        assert result.exitcode == 0
        assert "18" in result.stdout
        assert "640x360" in result.stdout
        assert "720p" in result.stdout

    def test_info_failure_returns_1(self, fake_ytdlp):
        result = fake_ytdlp.run(["info", "http://example.com/missing"])
        assert result.exitcode == 1
        assert "ERROR" in result.stderr


class TestDownload:
    def test_downloads_to_output_dir(self, fake_ytdlp, tmp_path):
        out = tmp_path / "videos"
        result = fake_ytdlp.run(
            ["download", "http://example.com/video", "--output-dir", str(out)])
        assert result.exitcode == 0
        assert out.is_dir()
        target = out / "Fake Test Video [fake123].mp4"
        assert target.is_file()
        assert f"Downloaded: {target}" in result.stdout

    def test_default_flags(self, fake_ytdlp):
        fake_ytdlp.run(["download", "http://example.com/video"])
        log = fake_ytdlp.read_log()[0]
        assert "--no-overwrites" in log
        assert "--no-playlist" in log
        assert "--no-progress" in log
        assert "-o" in log
        assert "--print" in log

    def test_overwrite_flag(self, fake_ytdlp):
        fake_ytdlp.run(["download", "http://example.com/video", "--overwrite"])
        assert "--force-overwrites" in fake_ytdlp.read_log()[0]

    def test_format_option(self, fake_ytdlp):
        fake_ytdlp.run(
            ["download", "http://example.com/video",
             "--format", "bv*[height<=720]+ba/b"])
        log = fake_ytdlp.read_log()[0]
        assert "--format" in log
        assert "bv*[height<=720]+ba/b" in log

    def test_playlist_mode(self, fake_ytdlp):
        fake_ytdlp.run(
            ["download", "http://example.com/playlist",
             "--playlist", "--playlist-items", "1:3,5"])
        log = fake_ytdlp.read_log()[0]
        assert "--no-playlist" not in log
        assert "--playlist-items" in log
        assert "1:3,5" in log

    def test_cookies_from_browser(self, fake_ytdlp):
        fake_ytdlp.run(
            ["download", "http://example.com/video", "--cookies-from-browser", "firefox"])
        assert "--cookies-from-browser" in fake_ytdlp.read_log()[0]

    def test_limit_rate(self, fake_ytdlp):
        fake_ytdlp.run(["download", "http://example.com/video", "--limit-rate", "2M"])
        log = fake_ytdlp.read_log()[0]
        assert "--limit-rate" in log
        assert "2M" in log

    def test_proxy(self, fake_ytdlp):
        fake_ytdlp.run(
            ["download", "http://example.com/video", "--proxy", "socks5://127.0.0.1:1080/"])
        assert "socks5://127.0.0.1:1080/" in fake_ytdlp.read_log()[0]

    def test_impersonate_flag(self, fake_ytdlp):
        fake_ytdlp.run(["download", "http://example.com/video", "--impersonate"])
        log = fake_ytdlp.read_log()[0]
        assert "--extractor-args" in log
        assert "generic:impersonate" in log

    def test_no_impersonate_by_default(self, fake_ytdlp):
        fake_ytdlp.run(["download", "http://example.com/video"])
        assert "--extractor-args" not in fake_ytdlp.read_log()[0]

    def test_subs(self, fake_ytdlp):
        fake_ytdlp.run(["download", "http://example.com/video", "--subs"])
        log = fake_ytdlp.read_log()[0]
        assert "--write-subs" in log
        assert "--write-auto-subs" in log
        assert "--sub-langs" in log

    def test_embed_thumbnail(self, fake_ytdlp):
        fake_ytdlp.run(["download", "http://example.com/video", "--embed-thumbnail"])
        assert "--embed-thumbnail" in fake_ytdlp.read_log()[0]

    def test_audio_only(self, fake_ytdlp, tmp_path):
        out = tmp_path / "audio"
        result = fake_ytdlp.run(
            ["download", "http://example.com/video",
             "--audio-only", "--audio-format", "m4a", "--output-dir", str(out)])
        assert result.exitcode == 0
        log = fake_ytdlp.read_log()[0]
        assert "-x" in log
        assert "--audio-format" in log
        assert "m4a" in log
        assert (out / "Fake Test Video [fake123].m4a").is_file()


class TestAudio:
    def test_extracts_audio_default_mp3(self, fake_ytdlp, tmp_path):
        out = tmp_path / "audio"
        result = fake_ytdlp.run(["audio", "http://example.com/video", "--output-dir", str(out)])
        assert result.exitcode == 0
        log = fake_ytdlp.read_log()[0]
        assert "-x" in log
        assert "--audio-format" in log
        assert "mp3" in log
        assert (out / "Fake Test Video [fake123].mp3").is_file()


class TestValidation:
    def test_missing_url(self, fake_ytdlp):
        result = fake_ytdlp.run(["download"])
        assert result.exitcode == 2
        assert "url" in result.stderr

    def test_url_starting_with_dash(self, fake_ytdlp):
        result = fake_ytdlp.run(["download", "-fakeurl"])
        assert result.exitcode == 2

    def test_bad_audio_format(self, fake_ytdlp):
        result = fake_ytdlp.run(
            ["download", "http://example.com/video", "--audio-only", "--audio-format", "wma"])
        assert result.exitcode == 2

    def test_bad_browser(self, fake_ytdlp):
        result = fake_ytdlp.run(
            ["download", "http://example.com/video", "--cookies-from-browser", "netscape"])
        assert result.exitcode == 2

    def test_bad_limit_rate(self, fake_ytdlp):
        result = fake_ytdlp.run(
            ["download", "http://example.com/video", "--limit-rate", "fast"])
        assert result.exitcode == 2

    def test_bad_proxy(self, fake_ytdlp):
        result = fake_ytdlp.run(
            ["download", "http://example.com/video", "--proxy", "ftp://x"])
        assert result.exitcode == 2

    def test_bad_playlist_items(self, fake_ytdlp):
        result = fake_ytdlp.run(
            ["download", "http://example.com/video", "--playlist", "--playlist-items", "1 3"])
        assert result.exitcode == 2


class TestYtDlpFailure:
    def test_fake_fail_returns_1(self, fake_ytdlp, monkeypatch):
        monkeypatch.setenv("FAKE_FAIL", "1")
        result = fake_ytdlp.run(["download", "http://example.com/video"])
        assert result.exitcode == 1
        assert "forced failure" in result.stderr


class TestVersion:
    def test_prints_versions(self, fake_ytdlp):
        result = fake_ytdlp.run(["version"])
        assert result.exitcode == 0
        assert "yt-dlp 2026.07.04" in result.stdout
        assert "ffmpeg" in result.stdout

    def test_reports_impersonation_available(self, fake_ytdlp):
        result = fake_ytdlp.run(["version"])
        assert result.exitcode == 0
        assert "impersonation" in result.stdout
        assert "available" in result.stdout

    def test_reports_impersonation_unavailable(self, fake_ytdlp, monkeypatch):
        monkeypatch.setenv("FAKE_NO_IMPERSONATE", "1")
        result = fake_ytdlp.run(["version"])
        assert result.exitcode == 0
        assert "UNAVAILABLE" in result.stdout
        assert "VIDEO_DOWNLOAD_YTDLP_BIN" in result.stdout


class TestVerbose:
    def test_prints_command(self, fake_ytdlp):
        result = fake_ytdlp.run(["download", "http://example.com/video", "--verbose"])
        assert result.exitcode == 0
        assert "yt-dlp" in result.stdout
