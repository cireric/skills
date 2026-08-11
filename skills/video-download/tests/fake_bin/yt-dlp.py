#!/usr/bin/env python3
"""Fake yt-dlp binary — logs argv, simulates -J metadata and downloads."""
import json
import os
import sys

FAKE_META = {
    "id": "fake123",
    "title": "Fake Test Video",
    "uploader": "Fake Channel",
    "duration": 125,
    "upload_date": "20260810",
    "formats": [
        {"format_id": "18", "ext": "mp4", "height": 360, "resolution": "640x360",
         "vcodec": "avc1", "acodec": "mp4a", "format_note": "360p"},
        {"format_id": "22", "ext": "mp4", "height": 720, "resolution": "1280x720",
         "vcodec": "avc1", "acodec": "mp4a", "format_note": "720p"},
    ],
}


def _log(argv: list) -> None:
    log_path = os.environ.get("FAKE_LOG")
    if log_path:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(argv) + "\n")


def _opt(argv: list, name: str) -> str:
    for i, arg in enumerate(argv):
        if arg == name and i + 1 < len(argv):
            return argv[i + 1]
    return ""


def _resolved_path(argv: list) -> str:
    """Resolve the -o template against the -P dir to the fake output path."""
    tmpl = _opt(argv, "-o")
    outdir = _opt(argv, "-P")
    ext = "mp4"
    if "-x" in argv:
        ext = _opt(argv, "--audio-format") or "mp3"
    name = (tmpl or "%(title)s [%(id)s].%(ext)s") \
        .replace("%(title)s", "Fake Test Video") \
        .replace("%(id)s", "fake123") \
        .replace("%(ext)s", ext)
    return os.path.join(outdir, name) if outdir else name


def main() -> None:
    argv = sys.argv[1:]
    _log(argv)

    if os.environ.get("FAKE_FAIL") == "1":
        print("Fake yt-dlp error: forced failure", file=sys.stderr)
        sys.exit(1)

    if "--version" in argv:
        print(os.environ.get("FAKE_VERSION", "2026.07.04"))
        sys.exit(0)

    if "--list-impersonate-targets" in argv:
        if os.environ.get("FAKE_NO_IMPERSONATE") == "1":
            print("Safari-18.0   Ios-18.0     curl_cffi (unavailable)")
        else:
            print("Safari-18.0   Ios-18.0     curl_cffi")
        sys.exit(0)

    url = argv[-1]
    if "-J" in argv:
        if "missing" in url:
            print("ERROR: [generic] missing: Unable to download webpage", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(FAKE_META))
        sys.exit(0)

    # download / --print path
    path = _resolved_path(argv)
    if path:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w") as f:
            f.write("fake video data")
    if "--print" in argv:
        print(path)
    sys.exit(0)


if __name__ == "__main__":
    main()
