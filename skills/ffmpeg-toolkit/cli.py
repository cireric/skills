#!/usr/bin/env python3
"""FFmpeg Toolkit CLI — wraps ffmpeg/ffprobe for common video processing.

Usage: cli.py <operation> [options] <input...> [output]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Sequence

FFMPEG_BIN: str = shutil.which("ffmpeg") or "ffmpeg"
FFPROBE_BIN: str = shutil.which("ffprobe") or "ffprobe"

_CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
_config = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))

# ── helpers ────────────────────────────────────────────────────────────────


def _parse_time(s: str) -> str:
    if not s:
        return "0"
    s = s.strip()
    try:
        return str(float(s))
    except ValueError:
        pass
    parts = s.split(":")
    if len(parts) == 2:
        return str(int(parts[0]) * 60 + float(parts[1]))
    if len(parts) == 3:
        return str(int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2]))
    raise ValueError(f"Invalid time format: {s!r}")


def _build_atempo(factor: float) -> str:
    stages: List[float] = []
    remaining = factor
    while remaining > 2.0:
        stages.append(2.0)
        remaining /= 2.0
    while remaining < 0.5:
        stages.append(0.5)
        remaining /= 0.5
    stages.append(round(remaining, 4))
    return ",".join(f"atempo={s}" for s in stages)


def _die(msg: str) -> int:
    print(msg, file=sys.stderr)
    return 2


def _exit_on_fail(result: "subprocess.CompletedProcess[str]") -> int:
    if result.returncode != 0:
        print(result.stderr.strip(), file=sys.stderr)
        return 1
    return 0


def _run_ffmpeg(args: List[str], verbose: bool = False) -> int:
    cmd = [FFMPEG_BIN] + args
    if verbose:
        print(" ".join(cmd))
    return _exit_on_fail(subprocess.run(cmd, capture_output=True, text=True))


def _val_in(path: Path) -> Optional[int]:
    if not path.is_file():
        return _die(f"Input file not found: {path}")
    return None


def _val_out(out: Path, overwrite: bool, whitelist: Sequence[str]) -> Optional[int]:
    ext = out.suffix.lower()
    if ext not in whitelist:
        return _die(f"Unsupported output extension {ext!r} for this operation. "
                     f"Allowed: {', '.join(whitelist)}")
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and not overwrite:
        return _die(f"Output file already exists: {out}  (use --overwrite to replace)")
    return None


def _ow(overwrite: bool) -> str:
    return "-y" if overwrite else "-n"


# ── subcommand handlers ──────────────────────────────────────────────────────


def cmd_info(args: argparse.Namespace) -> int:
    inp = Path(args.input)
    if (err := _val_in(inp)) is not None:
        return err
    result = subprocess.run(
        [FFPROBE_BIN, "-v", "error", "-print_format", "json",
         "-show_streams", "-show_format", str(inp)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(result.stderr.strip(), file=sys.stderr)
        return 1

    data = json.loads(result.stdout)
    fmt = data.get("format", {})
    streams = data.get("streams", [])
    dur_s = float(fmt.get("duration", 0))
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    size_b = int(float(fmt.get("size", 0)))

    print(f"时长: {int(dur_s) // 60:02d}:{int(dur_s) % 60:02d}")
    print(f"分辨率: {video.get('width', '?')}x{video.get('height', '?')}")
    print(f"视频编码: {video.get('codec_name', '未知')}")
    print(f"音频编码: {audio.get('codec_name', '无音频') if audio else '无音频'}")
    print(f"文件大小: {size_b / (1024 * 1024):.2f} MB"
          if size_b >= 1024 * 1024 else f"{size_b / 1024:.1f} KB")
    return 0


def cmd_convert(args: argparse.Namespace) -> int:
    inp, out, W = Path(args.input), Path(args.output), (
        ".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v", ".ts")
    if (err := _val_in(inp)) is not None or (err := _val_out(out, args.overwrite, W)) is not None:
        return err
    ffargs: List[str] = [_ow(args.overwrite), "-i", str(inp)]
    if args.video_codec:
        ffargs += ["-c:v", args.video_codec]
    ffargs.append(str(out))
    return _run_ffmpeg(ffargs, args.verbose)


def cmd_scale(args: argparse.Namespace) -> int:
    inp, out, W = Path(args.input), Path(args.output), (".mp4", ".mkv", ".webm", ".mov")
    if (err := _val_in(inp)) is not None or (err := _val_out(out, args.overwrite, W)) is not None:
        return err
    if not args.width and not args.height:
        return _die("At least one of --width or --height is required")
    if args.width is not None and not (16 <= args.width <= 7680):
        return _die(f"--width must be 16–7680, got {args.width}")
    if args.height is not None and not (16 <= args.height <= 4320):
        return _die(f"--height must be 16–4320, got {args.height}")
    if args.force:
        if not args.width or not args.height:
            return _die("--force requires both --width and --height")
        vf = f"scale={args.width}:{args.height}"
    elif args.width:
        vf = f"scale={args.width}:-2"
    else:
        vf = f"scale=-2:{args.height}"
    return _run_ffmpeg(
        [_ow(args.overwrite), "-i", str(inp), "-vf", vf, str(out)], args.verbose)


def cmd_compress(args: argparse.Namespace) -> int:
    inp, out, W = Path(args.input), Path(args.output), (".mp4", ".mkv", ".webm")
    if (err := _val_in(inp)) is not None or (err := _val_out(out, args.overwrite, W)) is not None:
        return err
    if not (0 <= args.crf <= 51):
        return _die(f"--crf must be 0–51, got {args.crf}")
    codec_map = {"h264": "libx264", "h265": "libx265", "vp9": "libvpx-vp9"}
    return _run_ffmpeg([
        _ow(args.overwrite), "-i", str(inp), "-c:v", codec_map[args.codec],
        "-crf", str(args.crf), "-preset", "medium", "-c:a", "aac", str(out),
    ], args.verbose)


def cmd_trim(args: argparse.Namespace) -> int:
    inp, out, W = Path(args.input), Path(args.output), (".mp4", ".mkv", ".webm", ".mov")
    if (err := _val_in(inp)) is not None or (err := _val_out(out, args.overwrite, W)) is not None:
        return err
    try:
        start = _parse_time(args.start)
    except ValueError as e:
        return _die(str(e))
    if not args.duration and not args.end:
        return _die("Either --duration or --end is required")
    if args.duration and args.end:
        return _die("Only one of --duration or --end allowed")
    try:
        if args.duration:
            duration = _parse_time(args.duration)
        else:
            dur_s = float(_parse_time(args.end)) - float(start)
            if dur_s <= 0:
                return _die(f"Duration must be positive (end – start = {dur_s:.1f}s)")
            duration = str(dur_s)
    except ValueError as e:
        return _die(str(e))
    return _run_ffmpeg([
        _ow(args.overwrite), "-ss", start, "-i", str(inp),
        "-t", duration, "-c:v", "libx264", "-c:a", "aac", str(out),
    ], args.verbose)


def cmd_concat(args: argparse.Namespace) -> int:
    out, W = Path(args.output), (".mp4", ".mkv", ".webm", ".mov")
    inputs = [Path(p) for p in args.inputs]
    if len(inputs) < 2:
        return _die("concat requires at least 2 input files")
    for p in inputs:
        if (err := _val_in(p)) is not None:
            return err
    if (err := _val_out(out, args.overwrite, W)) is not None:
        return err
    fd, list_path = tempfile.mkstemp(suffix=".txt", prefix="ffconcat_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for p in inputs:
                f.write(f"file '{p.resolve()}'\n")
        ffargs = [_ow(args.overwrite), "-f", "concat", "-safe", "0", "-i", list_path]
        if args.reencode:
            ffargs += ["-c:v", "libx264", "-c:a", "aac"]
        else:
            ffargs += ["-c", "copy"]
        ffargs.append(str(out))
        return _run_ffmpeg(ffargs, args.verbose)
    finally:
        os.unlink(list_path)


def cmd_audio(args: argparse.Namespace) -> int:
    inp, out = Path(args.input), Path(args.output)
    modes = sum([bool(args.extract), bool(args.replace), bool(args.mute)])
    if modes == 0:
        return _die("One of --extract, --replace, or --mute is required")
    if modes > 1:
        return _die("Only one of --extract, --replace, --mute is allowed")
    if (err := _val_in(inp)) is not None:
        return err

    if args.extract:
        W = (".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg")
        if (err := _val_out(out, args.overwrite, W)) is not None:
            return err
        ffargs = [_ow(args.overwrite), "-i", str(inp), "-vn", str(out)]
    elif args.replace:
        W = (".mp4", ".mkv", ".mov", ".webm")
        afile = Path(args.replace)
        if not afile.is_file():
            return _die(f"Audio file not found: {afile}")
        if (err := _val_out(out, args.overwrite, W)) is not None:
            return err
        ffargs = [_ow(args.overwrite), "-i", str(inp), "-i", str(afile),
                  "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", str(out)]
    else:
        W = (".mp4", ".mkv", ".mov", ".webm")
        if (err := _val_out(out, args.overwrite, W)) is not None:
            return err
        ffargs = [_ow(args.overwrite), "-i", str(inp), "-c:v", "copy", "-an", str(out)]
    return _run_ffmpeg(ffargs, args.verbose)


def cmd_gif(args: argparse.Namespace) -> int:
    inp, out = Path(args.input), Path(args.output)
    if (err := _val_in(inp)) is not None or (err := _val_out(out, args.overwrite, (".gif",))) is not None:
        return err
    if not (16 <= args.width <= 7680):
        return _die(f"--width must be 16–7680, got {args.width}")
    if not (1 <= args.fps <= 30):
        return _die(f"--fps must be 1–30, got {args.fps}")
    vf = ",".join([
        f"fps={args.fps}",
        f"scale={args.width}:-1:flags=lanczos",
        "split[s0][s1]", "[s0]palettegen[p]", "[s1][p]paletteuse",
    ])
    ffargs = [_ow(args.overwrite), "-i", str(inp)]
    if args.start:
        try:
            ffargs += ["-ss", _parse_time(args.start)]
        except ValueError as e:
            return _die(str(e))
    if args.duration:
        try:
            ffargs += ["-t", _parse_time(args.duration)]
        except ValueError as e:
            return _die(str(e))
    ffargs += ["-vf", vf, "-loop", "0", str(out)]
    return _run_ffmpeg(ffargs, args.verbose)


def cmd_speed(args: argparse.Namespace) -> int:
    inp, out, W = Path(args.input), Path(args.output), (".mp4", ".mkv", ".webm", ".mov")
    if (err := _val_in(inp)) is not None or (err := _val_out(out, args.overwrite, W)) is not None:
        return err
    if not (0.25 <= args.factor <= 4.0):
        return _die(f"--factor must be 0.25–4.0, got {args.factor}")
    return _run_ffmpeg([
        _ow(args.overwrite), "-i", str(inp),
        "-vf", f"setpts=PTS/{args.factor}",
        "-filter:a", _build_atempo(args.factor), str(out),
    ], args.verbose)


def cmd_rotate(args: argparse.Namespace) -> int:
    inp, out, W = Path(args.input), Path(args.output), (".mp4", ".mkv", ".webm", ".mov")
    if (err := _val_in(inp)) is not None or (err := _val_out(out, args.overwrite, W)) is not None:
        return err
    if args.degrees not in (90, 180, 270):
        return _die(f"--degrees must be 90, 180, or 270. Got: {args.degrees}")
    vf = {"90": "transpose=1", "180": "hflip,vflip", "270": "transpose=2"}[str(args.degrees)]
    return _run_ffmpeg(
        [_ow(args.overwrite), "-i", str(inp), "-vf", vf, str(out)], args.verbose)


def cmd_flip(args: argparse.Namespace) -> int:
    inp, out, W = Path(args.input), Path(args.output), (".mp4", ".mkv", ".webm", ".mov")
    if (err := _val_in(inp)) is not None or (err := _val_out(out, args.overwrite, W)) is not None:
        return err
    if not args.horizontal and not args.vertical:
        return _die("At least one of --horizontal or --vertical is required")
    parts = []
    if args.horizontal:
        parts.append("hflip")
    if args.vertical:
        parts.append("vflip")
    return _run_ffmpeg(
        [_ow(args.overwrite), "-i", str(inp), "-vf", ",".join(parts), str(out)], args.verbose)


# ── CLI setup ────────────────────────────────────────────────────────────────

HANDLERS = {
    "info": cmd_info, "convert": cmd_convert, "scale": cmd_scale,
    "compress": cmd_compress, "trim": cmd_trim, "concat": cmd_concat,
    "audio": cmd_audio, "gif": cmd_gif, "speed": cmd_speed,
    "rotate": cmd_rotate, "flip": cmd_flip,
}


def _build_parser() -> argparse.ArgumentParser:
    global_parser = argparse.ArgumentParser(add_help=False)
    global_parser.add_argument("--overwrite", action="store_true",
                               default=argparse.SUPPRESS)
    global_parser.add_argument("--verbose", action="store_true",
                               default=argparse.SUPPRESS)

    parser = argparse.ArgumentParser(description="FFmpeg Toolkit CLI")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    subs = parser.add_subparsers(dest="command", required=True)

    def _add(name, help, **kw):
        kw.setdefault("parents", [global_parser])
        return subs.add_parser(name, help=help, **kw)

    _add("info", "Print media file metadata").add_argument("input")

    p = _add("convert", "Convert media format")
    p.add_argument("--video-codec", default=None)
    p.add_argument("input"); p.add_argument("output")

    p = _add("scale", "Resize video")
    p.add_argument("--width", type=int, default=None)
    p.add_argument("--height", type=int, default=None)
    p.add_argument("--force", action="store_true")
    p.add_argument("input"); p.add_argument("output")

    p = _add("compress", "Compress video with CRF")
    p.add_argument("--crf", type=int, default=_config["default_crf"])
    p.add_argument("--codec", choices=["h264", "h265", "vp9"], default="h264")
    p.add_argument("input"); p.add_argument("output")

    p = _add("trim", "Trim a video segment")
    p.add_argument("--start", default="0")
    p.add_argument("--duration", default=None)
    p.add_argument("--end", default=None)
    p.add_argument("input"); p.add_argument("output")

    p = _add("concat", "Concatenate multiple files")
    p.add_argument("--reencode", action="store_true")
    p.add_argument("output"); p.add_argument("inputs", nargs="+")

    p = _add("audio", "Audio operations")
    p.add_argument("--extract", action="store_true")
    p.add_argument("--replace", default=None, metavar="AUDIOFILE")
    p.add_argument("--mute", action="store_true")
    p.add_argument("input"); p.add_argument("output")

    p = _add("gif", "Create animated GIF")
    p.add_argument("--width", type=int, default=_config["gif_default_width"])
    p.add_argument("--fps", type=int, default=_config["gif_default_fps"])
    p.add_argument("--start", default=None)
    p.add_argument("--duration", default=None)
    p.add_argument("input"); p.add_argument("output")

    p = _add("speed", "Change playback speed")
    p.add_argument("--factor", type=float, required=True)
    p.add_argument("input"); p.add_argument("output")

    p = _add("rotate", "Rotate video")
    p.add_argument("--degrees", type=int, required=True)
    p.add_argument("input"); p.add_argument("output")

    p = _add("flip", "Flip video (horizontal/vertical)")
    p.add_argument("--horizontal", action="store_true")
    p.add_argument("--vertical", action="store_true")
    p.add_argument("input"); p.add_argument("output")

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 2
    handler = HANDLERS.get(args.command)
    if handler is None:
        return _die(f"Unknown command: {args.command}")
    return handler(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
