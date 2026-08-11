#!/usr/bin/env python3
"""Fake ffmpeg binary — logs argv and optionally creates output file."""
import json
import os
import sys

VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v", ".ts"}
AUDIO_EXTS = {".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg"}
GIF_EXTS = {".gif"}
ALL_OUT_EXTS = VIDEO_EXTS | AUDIO_EXTS | GIF_EXTS


def main() -> None:
    log_path = os.environ.get("FAKE_LOG")
    if log_path:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(sys.argv[1:]) + "\n")

    if os.environ.get("FAKE_FAIL") == "1":
        print("Fake ffmpeg error: forced failure", file=sys.stderr)
        sys.exit(1)

    # Create output file from last non-flag, non-input, non-concat-list arg
    input_paths: list = []
    concat_list_idx: int = -1
    i = 0
    while i < len(sys.argv) - 1:
        arg = sys.argv[i]
        if arg == "-i":
            i += 1
            input_paths.append(sys.argv[i])
        elif arg == "-f" and sys.argv[i] == "concat":
            # concat mode: the next arg is the list file, then -i, then the list path again
            pass
        i += 1

    # Find the output path: last positional arg that ends with a known extension
    # and is not one of the input paths or the concat list
    known_paths = set(input_paths)
    output = None
    for arg in reversed(sys.argv[1:]):
        if arg.startswith("-"):
            continue
        ext = os.path.splitext(arg)[1].lower()
        if ext in ALL_OUT_EXTS and arg not in known_paths:
            output = arg
            break

    if output is not None:
        open(output, "w").close()


if __name__ == "__main__":
    main()
