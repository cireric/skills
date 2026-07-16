"""工具函数：文件名清理、指数退避、asyncio 配置."""

import asyncio
import json
import logging
import random
import re
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, cast

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """清理文件名，移除非法字符."""
    if not filename or not filename.strip():
        return "untitled"
    filename = filename.strip()
    invalid_chars = r'[<>:"/\\|?*\uff1a\uff1f\uff01\u300a\u300b]'
    filename = re.sub(invalid_chars, "", filename)
    filename = filename.replace(" ", "_")
    if len(filename) > max_length:
        filename = filename[:max_length]
    return filename or "untitled"


def load_state(state_file: str) -> dict[str, Any] | None:
    """加载状态文件."""
    path = Path(state_file)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return cast(dict[str, Any], json.load(f))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"加载状态文件失败 {state_file}: {e}")
        return None


def save_state(state_file: str, state: dict[str, Any]) -> None:
    """保存状态文件."""
    path = Path(state_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    state["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.error(f"保存状态文件失败 {state_file}: {e}")


def exponential_backoff(attempt: int, base: float = 1.0, max_wait: float = 60.0) -> float:
    """指数退避计算."""
    wait = min(base * (2**attempt), max_wait)
    jitter = random.uniform(0, min(1.0, max_wait - wait))
    return float(wait + jitter)


def configure_asyncio() -> None:
    """Configure asyncio for the current platform."""
    warnings.filterwarnings("ignore", category=ResourceWarning, message=".*unclosed.*")
    if sys.platform == "win32" and sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
