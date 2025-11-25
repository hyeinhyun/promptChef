from __future__ import annotations

"""Configuration and profile helpers."""

import json
from typing import Any, Dict

from ..config import CONFIG_PATH, DEFAULT_CONFIG
from ..models import Profile


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


def load_profile(fallback: Profile | None = None) -> Profile:
    config = load_config()
    data = config.get("profile") or {}
    if not data and fallback is not None:
        return fallback
    return Profile(**data)


def update_profile(profile_data: Dict[str, Any]) -> Profile:
    profile = Profile(**profile_data)
    config = load_config()
    config["profile"] = profile.model_dump()
    save_config(config)
    return profile
