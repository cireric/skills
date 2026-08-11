#!/usr/bin/env python3
"""Fake ffprobe binary — returns fixed JSON metadata."""
import json
import os
import sys

FIXED_OUTPUT = {
    "streams": [
        {
            "index": 0,
            "codec_name": "h264",
            "codec_type": "video",
            "width": 1920,
            "height": 1080,
        },
        {
            "index": 1,
            "codec_name": "aac",
            "codec_type": "audio",
        },
    ],
    "format": {
        "duration": "10.0",
        "size": "1234567",
        "bit_rate": "800000",
    },
}


def main() -> None:
    if os.environ.get("FAKE_FAIL") == "1":
        print("Fake ffprobe error: forced failure", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(FIXED_OUTPUT))


if __name__ == "__main__":
    main()
