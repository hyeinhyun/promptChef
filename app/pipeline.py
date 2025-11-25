from __future__ import annotations

"""Backward-compatible pipeline facade."""

from .services.pipeline_service import (
    auto_compose_and_run,
    compose_and_plan,
    compose_and_run,
    compose_with_plan,
    run_with_refine,
    save_feedback,
)

__all__ = [
    "compose_and_plan",
    "compose_with_plan",
    "compose_and_run",
    "run_with_refine",
    "auto_compose_and_run",
    "save_feedback",
]
