"""Test suite for ffmpeg-toolkit CLI.

Tests use fake ffmpeg/ffprobe binaries — never invoke real ffmpeg.
"""
import json
import os
from pathlib import Path

import pytest


# ── helpers ──────────────────────────────────────────────────────────


def _scrub_paths(args):
    """Replace absolute paths with '<PATH>' for clean assertion output."""
    import re

    return [re.sub(r"/[^\s]+\.txt", "<TMPLIST>", a) for a in args]


def _assert_token(logged_args, token, msg=None):
    """Assert `token` appears in the flattened argv."""
    flat = " ".join(logged_args)
    if isinstance(token, list):
        for t in token:
            assert t in logged_args, msg or f"Expected token {t!r} in {logged_args}"
    else:
        assert token in flat, msg or f"Expected token {token!r} in {flat}"


def _assert_no_token(logged_args, token, msg=None):
    """Assert `token` does NOT appear in the flattened argv."""
    flat = " ".join(logged_args)
    assert token not in flat, msg or f"Unexpected token {token!r} in {flat}"


# ── success path tests — one per subcommand ──────────────────────────


class TestInfo:
    def test_prints_metadata(self, fake_bins):
        result = fake_bins.run(["info", str(fake_bins.input)])
        assert result.exitcode == 0
        assert "1920x1080" in result.stdout
        assert "aac" in result.stdout
        assert "00:10" in result.stdout


class TestConvert:
    @pytest.mark.parametrize("ext", [".mp4", ".mkv", ".webm", ".mov"])
    def test_basic(self, fake_bins, ext):
        out = fake_bins.input.parent / f"out{ext}"
        result = fake_bins.run(["convert", str(fake_bins.input), str(out)])
        assert result.exitcode == 0
        assert out.exists()
        log = fake_bins.read_log()
        assert len(log) == 1
        _assert_token(log[0], "-i")
        _assert_token(log[0], str(out))

    def test_with_video_codec(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            ["convert", "--video-codec", "libx265", str(fake_bins.input), str(out)]
        )
        assert result.exitcode == 0
        log = fake_bins.read_log()
        _assert_token(log[0], ["-c:v", "libx265"])


class TestScale:
    def test_width_keeps_aspect(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            ["scale", "--width", "1920", str(fake_bins.input), str(out)]
        )
        assert result.exitcode == 0
        log = fake_bins.read_log()
        _assert_token(log[0], ["-vf", "scale=1920:-2"])

    def test_height_keeps_aspect(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            ["scale", "--height", "1080", str(fake_bins.input), str(out)]
        )
        assert result.exitcode == 0
        log = fake_bins.read_log()
        _assert_token(log[0], ["-vf", "scale=-2:1080"])

    def test_force_stretch(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            [
                "scale",
                "--width",
                "1920",
                "--height",
                "1080",
                "--force",
                str(fake_bins.input),
                str(out),
            ]
        )
        assert result.exitcode == 0
        log = fake_bins.read_log()
        _assert_token(log[0], ["-vf", "scale=1920:1080"])


class TestCompress:
    def test_defaults(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(["compress", str(fake_bins.input), str(out)])
        assert result.exitcode == 0
        log = fake_bins.read_log()
        _assert_token(log[0], ["-crf", "23"])
        _assert_token(log[0], ["-preset", "medium"])

    def test_custom_crf_and_codec(self, fake_bins):
        out = fake_bins.input.parent / "out.mkv"
        result = fake_bins.run(
            [
                "compress",
                "--crf",
                "18",
                "--codec",
                "h265",
                str(fake_bins.input),
                str(out),
            ]
        )
        assert result.exitcode == 0
        log = fake_bins.read_log()
        _assert_token(log[0], ["-crf", "18"])
        _assert_token(log[0], ["-c:v", "libx265"])


class TestTrim:
    def test_with_duration(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            [
                "trim",
                "--start",
                "10",
                "--duration",
                "30",
                str(fake_bins.input),
                str(out),
            ]
        )
        assert result.exitcode == 0
        log = fake_bins.read_log()
        _assert_token(log[0], "-ss")
        _assert_token(log[0], "10.0")
        _assert_token(log[0], "-t")
        _assert_token(log[0], "30.0")

    def test_with_end_time(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            [
                "trim",
                "--start",
                "10.5",
                "--end",
                "40.5",
                str(fake_bins.input),
                str(out),
            ]
        )
        assert result.exitcode == 0
        log = fake_bins.read_log()
        _assert_token(log[0], ["-ss", "10.5"])
        _assert_token(log[0], ["-t", "30.0"])

    def test_time_hhmmss_format(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            [
                "trim",
                "--start",
                "1:00",
                "--duration",
                "1:30",
                str(fake_bins.input),
                str(out),
            ]
        )
        assert result.exitcode == 0
        log = fake_bins.read_log()
        _assert_token(log[0], ["-ss", "60.0"])
        _assert_token(log[0], ["-t", "90.0"])


class TestConcat:
    def test_basic(self, fake_bins):
        in2 = fake_bins.input.parent / "in2.mp4"
        in2.write_text("fake2")
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            [
                "concat",
                str(out),
                str(fake_bins.input),
                str(in2),
            ]
        )
        assert result.exitcode == 0
        assert out.exists()
        log = fake_bins.read_log()
        assert len(log) == 1
        _assert_token(log[0], ["-f", "concat"])
        _assert_token(log[0], ["-safe", "0"])
        # the temp list file path should be present
        flat = " ".join(log[0])
        assert ".txt" in flat  # concat list file

    def test_reencode(self, fake_bins):
        in2 = fake_bins.input.parent / "in2.mp4"
        in2.write_text("fake2")
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            [
                "concat",
                "--reencode",
                str(out),
                str(fake_bins.input),
                str(in2),
            ]
        )
        assert result.exitcode == 0
        log = fake_bins.read_log()
        _assert_token(log[0], ["-c:v", "libx264"])


class TestAudio:
    def test_extract(self, fake_bins):
        out = fake_bins.input.parent / "out.mp3"
        result = fake_bins.run(
            ["audio", "--extract", str(fake_bins.input), str(out)]
        )
        assert result.exitcode == 0
        log = fake_bins.read_log()
        _assert_token(log[0], "-vn")

    def test_replace(self, fake_bins):
        audio = fake_bins.input.parent / "audio.m4a"
        audio.write_text("fake audio")
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            [
                "audio",
                "--replace",
                str(audio),
                str(fake_bins.input),
                str(out),
            ]
        )
        assert result.exitcode == 0
        log = fake_bins.read_log()
        _assert_token(log[0], ["-map", "0:v"])
        _assert_token(log[0], ["-map", "1:a"])

    def test_mute(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            ["audio", "--mute", str(fake_bins.input), str(out)]
        )
        assert result.exitcode == 0
        log = fake_bins.read_log()
        _assert_token(log[0], "-an")


class TestGif:
    def test_defaults(self, fake_bins):
        out = fake_bins.input.parent / "out.gif"
        result = fake_bins.run(["gif", str(fake_bins.input), str(out)])
        assert result.exitcode == 0
        log = fake_bins.read_log()
        flat = " ".join(log[0])
        assert "fps=10" in flat
        assert "palettegen" in flat
        assert "paletteuse" in flat
        _assert_token(log[0], ["-loop", "0"])

    def test_custom_params(self, fake_bins):
        out = fake_bins.input.parent / "out.gif"
        result = fake_bins.run(
            [
                "gif",
                "--width",
                "640",
                "--fps",
                "15",
                "--start",
                "5",
                "--duration",
                "3",
                str(fake_bins.input),
                str(out),
            ]
        )
        assert result.exitcode == 0
        log = fake_bins.read_log()
        flat = " ".join(log[0])
        assert "fps=15" in flat
        assert "scale=640:-1" in flat
        _assert_token(log[0], "-ss")
        flat = " ".join(log[0])
        assert "5.0" in flat
        assert "3.0" in flat


class TestSpeed:
    def test_factor_1(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            ["speed", "--factor", "1.0", str(fake_bins.input), str(out)]
        )
        assert result.exitcode == 0
        log = fake_bins.read_log()
        _assert_token(log[0], ["-vf", "setpts=PTS/1.0"])

    def test_factor_2_5_atempo_chain(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            ["speed", "--factor", "2.5", str(fake_bins.input), str(out)]
        )
        assert result.exitcode == 0
        log = fake_bins.read_log()
        _assert_token(log[0], ["-vf", "setpts=PTS/2.5"])
        # atempo chain: 2.0, 1.25
        _assert_token(log[0], ["-filter:a", "atempo=2.0,atempo=1.25"])

    def test_factor_0_4_atempo_chain(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            ["speed", "--factor", "0.4", str(fake_bins.input), str(out)]
        )
        assert result.exitcode == 0
        log = fake_bins.read_log()
        # atempo chain: 0.5, 0.8
        _assert_token(log[0], ["-filter:a", "atempo=0.5,atempo=0.8"])


class TestRotate:
    @pytest.mark.parametrize(
        "degrees,expected_vf",
        [
            (90, "transpose=1"),
            (180, "hflip,vflip"),
            (270, "transpose=2"),
        ],
    )
    def test_all_angles(self, fake_bins, degrees, expected_vf):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            [
                "rotate",
                "--degrees",
                str(degrees),
                str(fake_bins.input),
                str(out),
            ]
        )
        assert result.exitcode == 0
        log = fake_bins.read_log()
        _assert_token(log[0], ["-vf", expected_vf])


class TestFlip:
    def test_horizontal(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            ["flip", "--horizontal", str(fake_bins.input), str(out)]
        )
        assert result.exitcode == 0
        log = fake_bins.read_log()
        _assert_token(log[0], ["-vf", "hflip"])

    def test_vertical(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            ["flip", "--vertical", str(fake_bins.input), str(out)]
        )
        assert result.exitcode == 0
        log = fake_bins.read_log()
        _assert_token(log[0], ["-vf", "vflip"])

    def test_both(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            [
                "flip",
                "--horizontal",
                "--vertical",
                str(fake_bins.input),
                str(out),
            ]
        )
        assert result.exitcode == 0
        log = fake_bins.read_log()
        _assert_token(log[0], ["-vf", "hflip,vflip"])


# ── overwrite / global flags ──────────────────────────────────────────


class TestOverwrite:
    def test_default_no_overwrite_uses_n(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(["convert", str(fake_bins.input), str(out)])
        assert result.exitcode == 0
        log = fake_bins.read_log()
        _assert_token(log[0], "-n")
        _assert_no_token(log[0], "-y")

    def test_overwrite_uses_y(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            ["--overwrite", "convert", str(fake_bins.input), str(out)]
        )
        assert result.exitcode == 0
        log = fake_bins.read_log()
        _assert_token(log[0], "-y")
        _assert_no_token(log[0], "-n")

    def test_overwrite_flag_after_subcommand_works(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        out.write_text("existing")
        result = fake_bins.run(
            ["convert", str(fake_bins.input), str(out), "--overwrite"]
        )
        assert result.exitcode == 0
        log = fake_bins.read_log()
        _assert_token(log[0], "-y")
        _assert_no_token(log[0], "-n")

    def test_output_exists_without_overwrite_fails(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        out.write_text("existing")  # pre-create
        result = fake_bins.run(["convert", str(fake_bins.input), str(out)])
        assert result.exitcode == 2
        assert result.stderr != ""

    def test_output_exists_with_overwrite_succeeds(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        out.write_text("existing")
        result = fake_bins.run(
            ["--overwrite", "convert", str(fake_bins.input), str(out)]
        )
        assert result.exitcode == 0
        log = fake_bins.read_log()
        _assert_token(log[0], "-y")


class TestVerbose:
    def test_verbose_prints_argv(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            ["--verbose", "convert", str(fake_bins.input), str(out)]
        )
        assert result.exitcode == 0
        # stdout should contain the ffmpeg command line
        assert "ffmpeg" in result.stdout.lower() or fake_bins.read_log()


# ── validation failure tests ──────────────────────────────────────────


class TestValidationInputMissing:
    def test_nonexistent_input(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(["convert", str(fake_bins.input.parent / "nope.mp4"), str(out)])
        assert result.exitcode == 2
        assert result.stderr != ""


class TestValidationBadExtension:
    @pytest.mark.parametrize(
        "subcmd,out_ext",
        [
            ("convert", ".xyz"),
            ("scale", ".xyz"),
            ("compress", ".xyz"),
            ("trim", ".xyz"),
            ("concat", ".xyz"),
            ("gif", ".mp4"),  # gif only allows .gif
            ("rotate", ".xyz"),
            ("flip", ".xyz"),
        ],
    )
    def test_bad_output_extension(self, fake_bins, subcmd, out_ext):
        out = fake_bins.input.parent / f"out{out_ext}"
        # Some subcommands need extra args
        extra = []
        if subcmd == "scale":
            extra = ["--width", "1920"]
        elif subcmd == "rotate":
            extra = ["--degrees", "90"]
        elif subcmd == "concat":
            in2 = fake_bins.input.parent / "in2.mp4"
            in2.write_text("fake2")
            result = fake_bins.run(
                [subcmd, str(out), str(fake_bins.input), str(in2)]
            )
            assert result.exitcode == 2
            assert result.stderr != ""
            return
        result = fake_bins.run(
            [subcmd, *extra, str(fake_bins.input), str(out)]
        )
        assert result.exitcode == 2
        assert result.stderr != ""


class TestValidationTimeFormat:
    def test_invalid_time(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            [
                "trim",
                "--start",
                "abc",
                "--duration",
                "30",
                str(fake_bins.input),
                str(out),
            ]
        )
        assert result.exitcode == 2
        assert result.stderr != ""


class TestValidationMissingRequired:
    def test_scale_no_dimensions(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(["scale", str(fake_bins.input), str(out)])
        assert result.exitcode == 2
        assert result.stderr != ""

    def test_audio_no_mode(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(["audio", str(fake_bins.input), str(out)])
        assert result.exitcode == 2
        assert result.stderr != ""

    def test_audio_two_modes(self, fake_bins):
        out = fake_bins.input.parent / "out.mp3"
        result = fake_bins.run(
            [
                "audio",
                "--extract",
                "--mute",
                str(fake_bins.input),
                str(out),
            ]
        )
        assert result.exitcode == 2
        assert result.stderr != ""

    def test_speed_no_factor(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(["speed", str(fake_bins.input), str(out)])
        assert result.exitcode == 2
        assert result.stderr != ""

    def test_rotate_bad_degrees(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            ["rotate", "--degrees", "45", str(fake_bins.input), str(out)]
        )
        assert result.exitcode == 2
        assert result.stderr != ""

    def test_flip_no_flag(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(["flip", str(fake_bins.input), str(out)])
        assert result.exitcode == 2
        assert result.stderr != ""

    def test_concat_too_few_inputs(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(["concat", str(out), str(fake_bins.input)])
        assert result.exitcode == 2
        assert result.stderr != ""

    def test_trim_no_time_range(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            ["trim", "--start", "10", str(fake_bins.input), str(out)]
        )
        assert result.exitcode == 2
        assert result.stderr != ""


class TestValidationOutOfRange:
    def test_crf_too_high(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            [
                "compress",
                "--crf",
                "60",
                str(fake_bins.input),
                str(out),
            ]
        )
        assert result.exitcode == 2
        assert result.stderr != ""

    def test_fps_out_of_range(self, fake_bins):
        out = fake_bins.input.parent / "out.gif"
        result = fake_bins.run(
            ["gif", "--fps", "0", str(fake_bins.input), str(out)]
        )
        assert result.exitcode == 2
        assert result.stderr != ""

    def test_speed_factor_too_high(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            ["speed", "--factor", "5.0", str(fake_bins.input), str(out)]
        )
        assert result.exitcode == 2
        assert result.stderr != ""

    def test_scale_width_too_low(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            ["scale", "--width", "8", str(fake_bins.input), str(out)]
        )
        assert result.exitcode == 2
        assert result.stderr != ""


# ── ffmpeg failure test ───────────────────────────────────────────────


class TestFfmpegFailure:
    def test_fake_fail_returns_1(self, fake_bins, monkeypatch):
        monkeypatch.setenv("FAKE_FAIL", "1")
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(["convert", str(fake_bins.input), str(out)])
        assert result.exitcode == 1
        assert "Fake ffmpeg error" in result.stderr


# ── edge-case tests ───────────────────────────────────────────────────


class TestAutoCreateOutputDir:
    def test_creates_missing_output_dir(self, fake_bins):
        out_dir = fake_bins.input.parent / "subdir"
        out = out_dir / "out.mp4"
        assert not out_dir.exists()
        result = fake_bins.run(["convert", str(fake_bins.input), str(out)])
        assert result.exitcode == 0
        assert out_dir.exists()


class TestSpeedExactFactor:
    def test_factor_4_point_0(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            ["speed", "--factor", "4.0", str(fake_bins.input), str(out)]
        )
        assert result.exitcode == 0
        log = fake_bins.read_log()
        _assert_token(log[0], ["-filter:a", "atempo=2.0,atempo=2.0"])

    def test_factor_0_point_25(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            ["speed", "--factor", "0.25", str(fake_bins.input), str(out)]
        )
        assert result.exitcode == 0
        log = fake_bins.read_log()
        _assert_token(log[0], ["-filter:a", "atempo=0.5,atempo=0.5"])


class TestTrimDefaults:
    def test_start_defaults_to_zero(self, fake_bins):
        out = fake_bins.input.parent / "out.mp4"
        result = fake_bins.run(
            [
                "trim",
                "--duration",
                "30",
                str(fake_bins.input),
                str(out),
            ]
        )
        assert result.exitcode == 0
        log = fake_bins.read_log()
        _assert_token(log[0], "-ss")
        _assert_token(log[0], "0.0")
