"""ffmpeg-toolkit 运行入口 — 实际实现在 ffmpeg_toolkit 包内.

保留此入口以维持 `skills/ffmpeg-toolkit/cli.py` 调用路径不变。
"""

import sys

from ffmpeg_toolkit.cli import main

if __name__ == "__main__":
    sys.exit(main())
