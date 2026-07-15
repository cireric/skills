"""各平台 CSS 选择器配置."""

import logging
import re
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_SKILL_DIR = Path(__file__).parent.parent


class Platform(Enum):
    """支持的平台."""

    WECHAT = "wechat"
    ZHIHU = "zhihu"
    JIANSHU = "jianshu"
    BILIBILI = "bilibili"
    GENERIC = "generic"


def load_platform_configs(yaml_path: Path | str) -> dict[Platform, dict[str, Any]]:
    """从 YAML 文件加载平台配置."""
    yaml_path = Path(yaml_path)
    with open(yaml_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    platforms_data = raw.get("platforms", {})
    configs: dict[Platform, dict[str, Any]] = {}
    for key, value in platforms_data.items():
        platform = Platform(key)
        configs[platform] = value
    return configs


_PLATFORM_CONFIGS: dict[Platform, dict[str, Any]] | None = None


def get_platform_configs() -> dict[Platform, dict[str, Any]]:
    """获取所有平台配置（从 platforms.yaml 加载）."""
    global _PLATFORM_CONFIGS
    if _PLATFORM_CONFIGS is None:
        _PLATFORM_CONFIGS = load_platform_configs(_SKILL_DIR / "platforms.yaml")
    return _PLATFORM_CONFIGS.copy()


def detect_platform(url: str) -> Platform:
    """根据 URL 检测平台."""
    configs = get_platform_configs()
    for platform, config in configs.items():
        if platform == Platform.GENERIC:
            continue
        patterns = config.get("article_patterns", []) + config.get("list_patterns", [])
        for pattern in patterns:
            if re.search(pattern, url):
                return platform
    return Platform.GENERIC


def get_platform_config(platform: Platform) -> dict[str, Any]:
    """获取平台配置."""
    configs = get_platform_configs()
    return configs.get(platform, configs[Platform.GENERIC])


def is_article_page(url: str, platform: Platform | None = None) -> bool:
    """判断是否为文章页."""
    if platform is None:
        platform = detect_platform(url)
    config = get_platform_config(platform)
    patterns = config.get("article_patterns", [])
    return any(re.search(pattern, url) for pattern in patterns)


def is_list_page(url: str, platform: Platform | None = None) -> bool:
    """判断是否为列表页."""
    if platform is None:
        platform = detect_platform(url)
    config = get_platform_config(platform)
    patterns = config.get("list_patterns", [])
    return any(re.search(pattern, url) for pattern in patterns)
