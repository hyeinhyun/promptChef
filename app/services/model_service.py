from __future__ import annotations

"""Model selection helpers."""

from typing import Dict, Tuple

from ..config import AVAILABLE_MODELS
from .settings_service import load_config, save_config


def set_model(name: str) -> Tuple[str, Dict[str, str]]:
    config = load_config()
    if name not in AVAILABLE_MODELS:
        raise ValueError(f"지원하지 않는 모델입니다: {name}")
    config["model"] = name
    save_config(config)
    return name, config
