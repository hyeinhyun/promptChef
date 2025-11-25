from __future__ import annotations

"""Evaluation utilities for generated drafts."""

import re
from typing import List

from ..models import EvalCheck, EvalReport, PlannerPlan


def build_eval_checks(draft: str, plan: PlannerPlan) -> EvalCheck:
    sentences = [segment for segment in re.split(r"[.!?\n]+", draft) if segment.strip()]
    sentence_count_ok = 3 <= len(sentences) <= 6
    has_title = draft.startswith("제목:")
    tone_match = True
    actions_present = "Action items" in draft or "Action" in draft
    concise = len(draft.split()) <= 180
    numbers_formatted = "%" in draft or bool(re.search(r"\d", draft))
    honorifics = any(word in draft for word in ["습니다", "드립니다", "해주세요"])
    avoids_overpromising = "확실" not in draft and "보장" not in draft

    return EvalCheck(
        has_title=has_title,
        sentence_count_ok=sentence_count_ok,
        tone_match=tone_match,
        actions_present=actions_present,
        concise=concise,
        numbers_formatted=numbers_formatted,
        honorifics=honorifics,
        avoids_overpromising=avoids_overpromising,
    )


def collect_eval_suggestions(checks: EvalCheck, plan: PlannerPlan) -> List[str]:
    suggestions: List[str] = []
    if not checks.sentence_count_ok:
        suggestions.append("문장 수 3~5개 준수 필요")
    if not checks.actions_present and "Action items" in plan.constraints:
        suggestions.append("Action items를 명시하세요")
    return suggestions


def evaluate(draft: str, plan: PlannerPlan) -> EvalReport:
    checks = build_eval_checks(draft, plan)
    suggestions = collect_eval_suggestions(checks, plan)
    score = max(0.4, 1 - len(suggestions) * 0.1)
    return EvalReport(
        score=round(score, 2),
        checks=checks,
        suggestions=suggestions or ["전체적으로 요구사항을 충족했습니다."],
    )
