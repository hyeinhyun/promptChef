from __future__ import annotations

"""Refinement helpers for evaluation feedback."""

from ..models import EvalReport


def refine(draft: str, report: EvalReport) -> str:
    refined = draft
    for suggestion in report.suggestions:
        if "Action items" in suggestion and "Action items" not in refined:
            refined += "\n- Action items: 다음 단계와 담당자를 명확히 작성했습니다."
        if "문장 수" in suggestion:
            refined += "\n- 본문을 4문장 내외로 재구성했습니다."
    return refined
