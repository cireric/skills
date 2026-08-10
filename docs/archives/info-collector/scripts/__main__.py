"""Allow running as `python -m scripts` from the skill directory."""

import os

# Force UTF-8 mode so stdin/stdout/file IO decode UTF-8 correctly on Windows
# (cp936 would otherwise mangle CJK content into surrogate characters).
os.environ.setdefault("PYTHONUTF8", "1")

from .cli import main

if __name__ == "__main__":
    main()
