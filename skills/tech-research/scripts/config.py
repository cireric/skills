from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ResearchConfig:
    output_dir: str = "reports"
    lang: str = "zh"


DEFAULT_CONFIG = ResearchConfig()
_CONFIG_FILENAME = "config.json"


def get_config_path(skill_dir: Path | None = None) -> Path:
    if skill_dir is None:
        skill_dir = Path(__file__).resolve().parent.parent
    return skill_dir / _CONFIG_FILENAME


def load_config(skill_dir: Path | None = None) -> ResearchConfig | None:
    path = get_config_path(skill_dir)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return ResearchConfig(
            output_dir=data.get("output_dir", DEFAULT_CONFIG.output_dir),
            lang=data.get("lang", DEFAULT_CONFIG.lang),
        )
    except (json.JSONDecodeError, KeyError):
        return None


def save_config(config: ResearchConfig, skill_dir: Path | None = None) -> Path:
    path = get_config_path(skill_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "output_dir": config.output_dir,
                "lang": config.lang,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    return path


_NON_ASCII = re.compile(r"[^\x20-\x7e]")
_NON_FILENAME = re.compile(r"[^a-z0-9]+")
_MULTI_DASH = re.compile(r"-{2,}")


def _slugify(text: str) -> str:
    text = text.lower()
    text = _NON_ASCII.sub("", text)
    text = _NON_FILENAME.sub("-", text)
    text = _MULTI_DASH.sub("-", text)
    text = text.strip("-")
    return text or "research"


def resolve_output_path(topic: str, config: ResearchConfig, project_root: Path) -> Path:
    from datetime import date

    today = date.today().isoformat()
    kebab_topic = _slugify(topic)
    filename = f"{today}-{kebab_topic}-research.md"
    out_dir = Path(config.output_dir)
    if not out_dir.is_absolute():
        out_dir = project_root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / filename
