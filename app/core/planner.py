from __future__ import annotations

"""Planner logic for PromptChef."""

from typing import List, Sequence

from ..models import PlannerPlan
from ..utils.constraints import (
    BASE_CONSTRAINTS,
    BUSINESS_TONES,
    CONSTRAINT_HINTS,
    TASK_CONSTRAINTS,
    TASK_KEYWORDS,
    TASK_OUTPUT_FORMS,
    adjust_confidence,
    dedupe_preserve_order,
)


def infer_tone(preferred: str | None) -> str:
    if preferred and preferred.lower() in BUSINESS_TONES:
        return preferred.lower()
    return "formal"


def detect_task(user_input: str) -> str:
    lowered = user_input.lower()
    for task, keywords in TASK_KEYWORDS.items():
        if any(keyword in user_input or keyword in lowered for keyword in keywords):
            return task
    return "general_brief"


def compose_constraints(task_type: str) -> List[str]:
    task_specific = TASK_CONSTRAINTS.get(task_type, [])
    return list(BASE_CONSTRAINTS) + task_specific


def merge_constraints(
    base_constraints: Sequence[str], user_input: str, llm_suggestions: List[str]
) -> List[str]:
    updated = list(base_constraints)
    lowered = user_input.lower()

    for keywords, suggestion, constraint in CONSTRAINT_HINTS:
        if any(keyword in lowered for keyword in keywords):
            llm_suggestions.append(suggestion)
            updated.append(constraint)

    return dedupe_preserve_order(updated)


def ensure_action_items_requirement(
    task_type: str, constraints: List[str], llm_suggestions: List[str]
) -> List[str]:
    requires_actions = any("action" in constraint.lower() for constraint in constraints)
    if task_type in {"summary_email", "general_brief"} and not requires_actions:
        llm_suggestions.append("후속 조치가 드러나도록 Action items 제약을 추가합니다.")
        constraints.append("Action items 2개 이상 포함")
    return constraints


def adjust_tone(current_tone: str, user_input: str, llm_suggestions: List[str]) -> str:
    if "친근" in user_input and current_tone == "formal":
        llm_suggestions.append("요청에 맞게 친근한 톤으로 전환합니다.")
        return "friendly"
    return current_tone


def verify_plan_with_llm(plan: PlannerPlan, user_input: str) -> PlannerPlan:
    """Simulate an agentic LLM pass that critiques and tightens the plan."""

    llm_suggestions: List[str] = []
    updated_constraints = merge_constraints(plan.constraints, user_input, llm_suggestions)
    updated_constraints = ensure_action_items_requirement(
        plan.task_type, updated_constraints, llm_suggestions
    )
    updated_constraints = dedupe_preserve_order(updated_constraints)
    tone = adjust_tone(plan.tone, user_input, llm_suggestions)
    confidence = adjust_confidence(plan.confidence, updated_constraints)
    notes = " / ".join(llm_suggestions) if llm_suggestions else "LLM 검증: 주요 제약 충족 확인"

    return PlannerPlan(
        task_type=plan.task_type,
        output_form=plan.output_form,
        audience=plan.audience,
        tone=tone,
        constraints=updated_constraints,
        confidence=confidence,
        notes=notes,
    )


def planner(request) -> PlannerPlan:
    task = detect_task(request.user_input)
    tone = infer_tone(request.profile.tone_pref)
    constraints = compose_constraints(task)
    confidence = 0.75 if request.profile.today_goal else 0.65
    output_form = TASK_OUTPUT_FORMS.get(task, "간결한 비즈니스 요약")
    initial_plan = PlannerPlan(
        task_type=task,
        output_form=output_form,
        audience=request.profile.role or "업무 상사",
        tone=tone,
        constraints=constraints,
        confidence=confidence,
    )

    return verify_plan_with_llm(initial_plan, request.user_input)
