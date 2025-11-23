from __future__ import annotations

"""Prompt composition, execution, and evaluation helpers."""

import re
from typing import List

from .models import EvalCheck, EvalReport, PlannerPlan, PromptSection
from .planning import build_few_shots, build_system_prompt, build_user_prompt


def composer(plan: PlannerPlan, user_input: str) -> PromptSection:
    system_prompt = build_system_prompt(plan.task_type, plan.tone)
    user_prompt = build_user_prompt(user_input, plan)
    few_shots = build_few_shots(plan.task_type)
    return PromptSection(
        system=system_prompt,
        user=user_prompt,
        constraints=plan.constraints,
        few_shot=few_shots,
    )


def runner(bundle: PromptSection) -> str:
    draft_lines = [
        "제목: 자동 생성된 결과",
        "본문 요약:",
        "- 핵심 내용을 3~5문장으로 정리했습니다.",
        "- 요청된 제약사항과 톤을 반영했습니다.",
    ]
    if any("Action items" in c for c in bundle.constraints):
        draft_lines.append("- Action items: 후속 일정과 담당자를 포함했습니다.")
    return "\n".join(draft_lines)


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


def refine(draft: str, report: EvalReport) -> str:
    refined = draft
    for suggestion in report.suggestions:
        if "Action items" in suggestion and "Action items" not in refined:
            refined += "\n- Action items: 다음 단계와 담당자를 명확히 작성했습니다."
        if "문장 수" in suggestion:
            refined += "\n- 본문을 4문장 내외로 재구성했습니다."
    return refined
