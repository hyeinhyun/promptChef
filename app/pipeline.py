from __future__ import annotations

import random
import re
import time
from typing import Iterable, List, Sequence

from .models import (
    ComposeAndRunRequest,
    ComposeAndRunResponse,
    EvalCheck,
    EvalReport,
    PlannerPlan,
    PromptSection,
    RunMeta,
)

BUSINESS_TONES = {
    "formal": "격식 있고 간결한 존댓말",
    "friendly": "친근하지만 예의 있는 톤",
    "apology": "정중한 사과 톤",
}
TASK_KEYWORDS = {
    "insight_extraction": {"표", "insight"},
    "style_transfer": {"공지", "톤"},
    "summary_email": {"회의", "보고"},
}
TASK_OUTPUT_FORMS = {
    "summary_email": "보고용 요약 이메일",
    "insight_extraction": "3~5개 불릿 인사이트",
    "style_transfer": "톤 변환 공지문",
    "general_brief": "간결한 비즈니스 요약",
}
BASE_CONSTRAINTS = [
    "제목은 1줄로 작성",
    "본문은 3~5문장으로 구성",
    "모든 문장은 존댓말로 작성",
    "과도한 확언/단정 금지",
]
TASK_CONSTRAINTS = {
    "summary_email": ["Action items 2개 이상 포함"],
    "insight_extraction": ["핵심 인사이트 3~5개 불릿으로 정리"],
}
CONSTRAINT_HINTS: Sequence[tuple[set[str], str, str]] = (
    (
        {"due", "deadline", "마감", "일정"},
        "마감과 담당자를 명시하라는 제약을 추가합니다.",
        "마감 일정과 담당자를 명확히 기재",
    ),
    (
        {"표", "table", "data", "%", "자료"},
        "숫자/데이터 근거를 표기하도록 요구합니다.",
        "숫자 근거를 함께 제시",
    ),
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


def dedupe_preserve_order(items: Iterable[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


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


def adjust_confidence(base_confidence: float, constraints: Sequence[str]) -> float:
    coverage_score = min(1.0, 0.55 + 0.05 * len(constraints))
    return round(min(1.0, base_confidence * 0.9 + coverage_score * 0.2), 2)


def build_few_shots(task_type: str) -> List[str]:
    examples = {
        "summary_email": [
            "[예시] 제목: 주간 마케팅 회의 요약\n- 핵심 결정 3개와 다음 액션을 숫자 목록으로 제공합니다.",
        ],
        "insight_extraction": [
            "[예시] 표 요약: 매출 상위 3개 상품과 감소 구간을 bullet으로 제시합니다.",
        ],
        "style_transfer": [
            "[예시] 동일 내용의 공지문을 더 정중한 톤으로 재작성합니다.",
        ],
    }
    return examples.get(task_type, [])


def build_system_prompt(task_type: str, tone: str) -> str:
    tone_desc = BUSINESS_TONES.get(tone, BUSINESS_TONES["formal"])
    return (
        "당신은 한국 비즈니스 글쓰기 어시스턴트입니다. "
        f"톤: {tone_desc}. 출력 형식을 반드시 준수하고 불필요한 장식을 피하세요."
    )


def build_user_prompt(user_input: str, plan: PlannerPlan) -> str:
    return (
        f"요청 유형: {plan.task_type}\n"
        f"출력 형식: {plan.output_form}\n"
        f"대상: {plan.audience}\n"
        f"추가 제약: {', '.join(plan.constraints)}\n"
        f"원문:\n{user_input.strip()}"
    )


def planner(request: ComposeAndRunRequest) -> PlannerPlan:
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
    # Stubbed model execution: join important parts for preview
    draft_lines = [
        "제목: 자동 생성된 결과",
        "본문 요약:",
        "- 핵심 내용을 3~5문장으로 정리했습니다.",
        "- 요청된 제약사항과 톤을 반영했습니다.",
    ]
    if any("Action items" in c for c in bundle.constraints):
        draft_lines.append("- Action items: 후속 일정과 담당자를 포함했습니다.")
    return "\n".join(draft_lines)


def evaluate(draft: str, plan: PlannerPlan) -> EvalReport:
    checks = build_eval_checks(draft, plan)
    suggestions = collect_eval_suggestions(checks, plan)
    score = max(0.4, 1 - len(suggestions) * 0.1)
    return EvalReport(
        score=round(score, 2),
        checks=checks,
        suggestions=suggestions or ["전체적으로 요구사항을 충족했습니다."],
    )


def build_eval_checks(draft: str, plan: PlannerPlan) -> EvalCheck:
    sentences = [segment for segment in re.split(r"[.!?\n]+", draft) if segment.strip()]
    sentence_count_ok = 3 <= len(sentences) <= 6
    has_title = draft.startswith("제목:")
    tone_match = True  # Stubbed; real check would use model/NLP
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


def refine(draft: str, report: EvalReport) -> str:
    refined = draft
    for suggestion in report.suggestions:
        if "Action items" in suggestion and "Action items" not in refined:
            refined += "\n- Action items: 다음 단계와 담당자를 명확히 작성했습니다."
        if "문장 수" in suggestion:
            refined += "\n- 본문을 4문장 내외로 재구성했습니다."
    return refined


def compose_and_run(request: ComposeAndRunRequest) -> ComposeAndRunResponse:
    start = time.time()
    plan = planner(request)
    bundle = composer(plan, request.user_input)
    draft_output = runner(bundle)
    eval_report = evaluate(draft_output, plan)
    final_output = refine(draft_output, eval_report)
    elapsed_ms = int((time.time() - start) * 1000)
    tokens_in = len(bundle.user.split()) + len(bundle.system.split())
    tokens_out = len(final_output.split())
    meta = RunMeta(tokens_in=tokens_in, tokens_out=tokens_out, latency_ms=elapsed_ms)
    return ComposeAndRunResponse(
        plan=plan,
        bundle=bundle,
        preview=draft_output,
        final_output=final_output,
        meta=meta,
    )


def save_feedback(feedback_id: str, rating: int, actions: List[str]) -> None:
    # Placeholder for DB insertion
    random.seed(feedback_id)
    _ = random.random()  # simulate some lightweight processing
    return None
