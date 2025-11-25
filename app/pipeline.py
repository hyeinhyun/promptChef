from __future__ import annotations

"""Backward-compatible pipeline facade."""

from .services.pipeline_service import (
    auto_compose_and_run,
    compose_and_run,
    compose_with_plan,
    save_feedback,
)

__all__ = [
    "compose_with_plan",
    "compose_and_run",
    "auto_compose_and_run",
    "save_feedback",
]
