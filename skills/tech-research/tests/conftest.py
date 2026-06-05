import sys
from pathlib import Path

_SKILL_DIR = str(Path(__file__).resolve().parent.parent)
if _SKILL_DIR not in sys.path:
    sys.path.insert(0, _SKILL_DIR)
