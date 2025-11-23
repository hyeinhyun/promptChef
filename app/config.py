from __future__ import annotations

"""Lightweight local configuration utilities for the CLI."""

import json
from pathlib import Path
from typing import Any, Dict, Tuple

from .models import Profile

CONFIG_PATH = Path.home() / ".promptchef_config.json"
DEFAULT_CONFIG = {"model": "basic-llm", "profile": {}}
AVAILABLE_MODELS = ("basic-llm", "analysis-pro", "creative-lab")


def _read_disk_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def load_config() -> Dict[str, Any]:
    disk_config = _read_disk_config()
    merged = {**DEFAULT_CONFIG, **disk_config}
    merged.setdefault("profile", {})
    merged.setdefault("model", DEFAULT_CONFIG["model"])
    return merged


def save_config(config: Dict[str, Any]) -> None:
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def set_model(name: str) -> Tuple[str, Dict[str, Any]]:
    config = load_config()
    if name not in AVAILABLE_MODELS:
        raise ValueError(f"지원하지 않는 모델입니다: {name}")
    config["model"] = name
    save_config(config)
    return name, config


def update_profile(profile_data: Dict[str, Any]) -> Profile:
    profile = Profile(**profile_data)
    config = load_config()
    config["profile"] = profile.model_dump()
    save_config(config)
    return profile


def load_profile(fallback: Profile | None = None) -> Profile:
    config = load_config()
    data = config.get("profile") or {}
    if not data and fallback is not None:
        return fallback
    return Profile(**data)
