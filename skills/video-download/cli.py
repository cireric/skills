"""video-download 运行入口 — 实际实现在 video_download 包内.

保留此入口以维持 `skills/video-download/cli.py` 调用路径不变。
"""

import sys

from video_download.cli import main

if __name__ == "__main__":
    sys.exit(main())
