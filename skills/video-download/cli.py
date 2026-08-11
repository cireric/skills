#!/usr/bin/env python3
"""Video Download CLI — wraps the yt-dlp binary for downloading videos.

Usage: cli.py <operation> [options] <url>

Operations:
  info      — fetch metadata (title, duration, resolutions) without downloading
  formats   — list available formats/resolutions as a table
  download  — download a video (single video by default, --playlist for playlists)
  audio     — download and extract the audio track (default mp3)
  version   — report yt-dlp and ffmpeg availability

Exit codes: 0 success · 1 yt-dlp failure (stderr has the reason) · 2 validation error.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

# Allow pointing at a yt-dlp build with curl_cffi (impersonation) support:
#   VIDEO_DOWNLOAD_YTDLP_BIN=/path/to/yt-dlp  (e.g. venv's `yt-dlp[curl-cffi]`)
YTDLP_BIN: str = os.environ.get("VIDEO_DOWNLOAD_YTDLP_BIN") or shutil.which("yt-dlp") or "yt-dlp"

_CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
_config = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))

OUT_TMPL = "%(title)s [%(id)s].%(ext)s"
AUDIO_FORMATS = ["mp3", "m4a", "opus", "wav", "flac", "aac"]
BROWSERS = ["chrome", "chromium", "edge", "firefox", "safari",
            "brave", "opera", "vivaldi", "whale"]
RATE_RE = re.compile(r"^\d+(\.\d+)?[KMG]?$", re.IGNORECASE)
PLAYLIST_ITEMS_RE = re.compile(r"^[0-9:,\-*]+$")
PROXY_PREFIXES = ("http://", "https://", "socks4://", "socks5://",
                  "socks4a://", "socks5h://")

# ── helpers ────────────────────────────────────────────────────────────────


def _die(msg: str) -> int:
    print(msg, file=sys.stderr)
    return 2


def _run(cmd: List[str], timeout: Optional[float] = None) -> Tuple[int, str, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print("yt-dlp timed out", file=sys.stderr)
        return 1, "", ""
    return result.returncode, result.stdout or "", result.stderr or ""


def _run_ytdlp(cmd: List[str], verbose: bool, timeout: Optional[float] = None
               ) -> Tuple[int, str, str]:
    if verbose:
        print(" ".join(cmd))
    return _run(cmd, timeout)


def _val_url(url: str) -> Optional[int]:
    if not url or not url.strip():
        return _die("Missing URL")
    if url.startswith("-"):
        return _die(f"URL must not start with '-': {url!r}")
    return None


def _pick_outdir(args_outdir: str) -> Optional[Path]:
    raw = args_outdir or str(_config.get("output_dir", ""))
    if not raw:
        return None
    p = Path(raw)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _fmt_duration(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _load_json(out: str) -> Optional[dict]:
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        print("Failed to parse yt-dlp JSON output", file=sys.stderr)
        return None
    if not isinstance(data, dict):
        print("Unexpected yt-dlp JSON output", file=sys.stderr)
        return None
    return data


# ── subcommand handlers ──────────────────────────────────────────────────────


def cmd_info(args: argparse.Namespace) -> int:
    if (err := _val_url(args.url)) is not None:
        return err
    timeout = float(_config.get("metadata_timeout", 120))
    rc, out, err_out = _run_ytdlp(
        [YTDLP_BIN, "-J", "--no-warnings", args.url], args.verbose, timeout)
    if rc != 0:
        print(err_out.strip() or f"yt-dlp failed (exit {rc})", file=sys.stderr)
        return 1
    data = _load_json(out)
    if data is None:
        return 1
    _print_info(data)
    return 0


def _print_info(d: dict) -> None:
    if "entries" in d:  # playlist
        entries = [e for e in (d.get("entries") or []) if e]
        print(f"Playlist: {d.get('title', '?')} ({len(entries)} videos)")
        for e in entries[:10]:
            print(f"  - {e.get('title', '?')} [{e.get('id', '?')}]")
        return
    print(f"Title: {d.get('title', '?')}")
    print(f"ID: {d.get('id', '?')}")
    if d.get("uploader"):
        print(f"Uploader: {d['uploader']}")
    if d.get("duration"):
        print(f"Duration: {_fmt_duration(d['duration'])}")
    if d.get("upload_date"):
        print(f"Upload date: {d['upload_date']}")
    fmts = d.get("formats") or []
    heights = sorted({f.get("height") for f in fmts if f.get("height")})
    if heights:
        print("Resolutions: " + ", ".join(f"{h}p" for h in heights))
    else:
        print(f"Formats: {len(fmts)}")


def cmd_formats(args: argparse.Namespace) -> int:
    if (err := _val_url(args.url)) is not None:
        return err
    timeout = float(_config.get("metadata_timeout", 120))
    rc, out, err_out = _run_ytdlp(
        [YTDLP_BIN, "-J", "--no-warnings", args.url], args.verbose, timeout)
    if rc != 0:
        print(err_out.strip() or f"yt-dlp failed (exit {rc})", file=sys.stderr)
        return 1
    data = _load_json(out)
    if data is None:
        return 1
    fmts = data.get("formats") or []
    if not fmts:
        print("No formats reported", file=sys.stderr)
        return 1
    print(f"{'format_id':<10} {'ext':<6} {'resolution':<14} {'vcodec':<10} {'acodec':<10} note")
    for f in fmts:
        res = f.get("resolution") or f.get("format_note") or ""
        vcodec = f.get("vcodec")
        acodec = f.get("acodec")
        if vcodec == "none":
            res = res or "audio only"
        vcodec = vcodec or "?"
        acodec = acodec or "?"
        print(f"{f.get('format_id', '?'):<10} {f.get('ext', '?'):<6} "
              f"{res:<14} {vcodec:<10} {acodec:<10} {f.get('format_note', '')}")
    return 0


def _build_download_cmd(args: argparse.Namespace, force_audio: bool
                        ) -> Tuple[Optional[int], List[str]]:
    if (err := _val_url(args.url)) is not None:
        return err, []
    outdir = _pick_outdir(getattr(args, "output_dir", ""))
    if getattr(args, "format", None):
        if any(c in args.format for c in "\r\n\x00"):
            return _die("Invalid --format value"), []
    if getattr(args, "limit_rate", None) and not RATE_RE.match(args.limit_rate):
        return _die(f"Invalid --limit-rate {args.limit_rate!r} (use e.g. 500K, 4.2M, 1G)"), []
    if getattr(args, "proxy", None) and not args.proxy.startswith(PROXY_PREFIXES):
        return _die(f"Invalid --proxy {args.proxy!r} (use http://, https://, socks4://, socks5://)"), []
    if getattr(args, "playlist_items", None) and not PLAYLIST_ITEMS_RE.match(args.playlist_items):
        return _die(f"Invalid --playlist-items {args.playlist_items!r} (e.g. 1:3,7)"), []

    cmd: List[str] = [YTDLP_BIN, "--no-progress"]
    overwrite = getattr(args, "overwrite", False) or bool(_config.get("overwrite", False))
    cmd.append("--force-overwrites" if overwrite else "--no-overwrites")
    if not getattr(args, "playlist", False):
        cmd.append("--no-playlist")
    if getattr(args, "playlist_items", None):
        cmd += ["--playlist-items", args.playlist_items]
    if getattr(args, "format", None):
        cmd += ["--format", args.format]
    if getattr(args, "limit_rate", None):
        cmd += ["--limit-rate", args.limit_rate]
    if getattr(args, "cookies_from_browser", None):
        cmd += ["--cookies-from-browser", args.cookies_from_browser]
    if getattr(args, "cookies", None):
        cmd += ["--cookies", args.cookies]
    if getattr(args, "proxy", None):
        cmd += ["--proxy", args.proxy]
    if getattr(args, "impersonate", False):
        cmd += ["--extractor-args", "generic:impersonate"]
    if getattr(args, "subs", False):
        langs = getattr(args, "sub_langs", None) or str(_config.get("default_sub_langs", "en.*,zh.*"))
        cmd += ["--write-subs", "--write-auto-subs", "--sub-langs", langs]
    if getattr(args, "embed_thumbnail", False):
        cmd += ["--embed-thumbnail"]
    if getattr(args, "restrict_filenames", False):
        cmd += ["--restrict-filenames"]
    if force_audio or getattr(args, "audio_only", False):
        cmd += ["-x", "--audio-format", args.audio_format, "--audio-quality", "0"]
    if outdir is not None:
        cmd += ["-P", str(outdir)]
    cmd += ["-o", OUT_TMPL, "--print", "after_move:filepath", args.url]
    return None, cmd


def _run_download(args: argparse.Namespace, force_audio: bool) -> int:
    err, cmd = _build_download_cmd(args, force_audio)
    if err is not None:
        return err
    if args.verbose:
        print(" ".join(cmd))
    rc, out, err_out = _run(cmd, timeout=None)
    if rc != 0:
        print(err_out.strip() or f"yt-dlp failed (exit {rc})", file=sys.stderr)
        return 1
    for line in out.splitlines():
        line = line.strip()
        if line:
            print(f"Downloaded: {line}")
    return 0


def cmd_download(args: argparse.Namespace) -> int:
    return _run_download(args, force_audio=False)


def cmd_audio(args: argparse.Namespace) -> int:
    return _run_download(args, force_audio=True)


def cmd_version(args: argparse.Namespace) -> int:
    rc, out, err_out = _run([YTDLP_BIN, "--version"])
    if rc != 0:
        print(err_out.strip() or f"yt-dlp failed (exit {rc})", file=sys.stderr)
        return 1
    print(f"yt-dlp {out.strip()}")
    ffmpeg = shutil.which("ffmpeg")
    print(f"ffmpeg: {ffmpeg or 'NOT FOUND — required for merging video+audio and audio extraction'}")
    impersonate = _impersonate_available()
    status = ("available — use --impersonate" if impersonate
              else 'UNAVAILABLE — brew yt-dlp lacks curl_cffi; set VIDEO_DOWNLOAD_YTDLP_BIN to a yt-dlp installed via pip "yt-dlp[curl-cffi]"')
    print(f"impersonation (Cloudflare bypass): {status}")
    return 0


def _impersonate_available() -> bool:
    rc, out, _ = _run([YTDLP_BIN, "--list-impersonate-targets"])
    if rc != 0:
        return False
    return "unavailable" not in out and "curl_cffi" in out


# ── argument parsing ─────────────────────────────────────────────────────────


def _add_download_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("url", help="video URL or ID")
    p.add_argument("--output-dir", default="", help="directory to save into (auto-created)")
    p.add_argument("--format", default="", help="yt-dlp format selector, e.g. 'bv*[height<=720]+ba/b'")
    p.add_argument("--audio-only", action="store_true", help="extract audio track after download")
    p.add_argument("--audio-format", choices=AUDIO_FORMATS,
                   default=str(_config.get("audio_format", "mp3")), help="audio codec")
    p.add_argument("--playlist", action="store_true", help="download whole playlist (default: single video)")
    p.add_argument("--playlist-items", default="", help="items to download, e.g. '1:3,5'")
    p.add_argument("--limit-rate", default="", help="download speed cap, e.g. '500K', '4.2M', '1G'")
    p.add_argument("--cookies-from-browser", choices=BROWSERS, default="",
                   help="use logged-in cookies from a browser (auth/bot walls)")
    p.add_argument("--cookies", default="", help="Netscape-format cookie file")
    p.add_argument("--proxy", default="", help="proxy URL, e.g. 'socks5://127.0.0.1:1080/'")
    p.add_argument("--impersonate", action="store_true",
                   help="impersonate a browser to bypass Cloudflare (requires yt-dlp with curl_cffi)")
    p.add_argument("--subs", action="store_true", help="write subtitles (auto + manual)")
    p.add_argument("--sub-langs", default="", help="subtitle languages, e.g. 'en.*,zh.*'")
    p.add_argument("--embed-thumbnail", action="store_true", help="embed thumbnail as cover art")
    p.add_argument("--restrict-filenames", action="store_true", help="ASCII-only, no spaces in filenames")
    p.add_argument("--overwrite", action="store_true", help="overwrite existing files")
    p.add_argument("--verbose", action="store_true", help="print the exact yt-dlp command")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cli.py", description="Video download via yt-dlp wrapper")
    sub = parser.add_subparsers(dest="operation", required=True)

    for name, help_text in (("info", "fetch metadata without downloading"),
                            ("formats", "list available formats")):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("url", help="video URL or ID")
        p.add_argument("--verbose", action="store_true")

    p_dl = sub.add_parser("download", help="download a video")
    _add_download_args(p_dl)

    p_au = sub.add_parser("audio", help="download and extract audio track")
    _add_download_args(p_au)

    sub.add_parser("version", help="report yt-dlp and ffmpeg availability")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 2
    handlers = {
        "info": cmd_info,
        "formats": cmd_formats,
        "download": cmd_download,
        "audio": cmd_audio,
        "version": cmd_version,
    }
    return handlers[args.operation](args)


if __name__ == "__main__":
    sys.exit(main())
