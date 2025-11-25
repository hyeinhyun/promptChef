from __future__ import annotations

"""Shared configuration defaults and constants."""

from pathlib import Path

CONFIG_PATH = Path.home() / ".promptchef_config.json"
DEFAULT_CONFIG = {"model": "basic-llm", "profile": {}}
AVAILABLE_MODELS = ("basic-llm", "analysis-pro", "creative-lab")
