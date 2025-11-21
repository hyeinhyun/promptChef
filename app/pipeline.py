from __future__ import annotations

import random
import re
import time
from typing import List

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


def infer_tone(preferred: str | None) -> str:
    if preferred and preferred.lower() in BUSINESS_TONES:
        return preferred.lower()
    return "formal"


def detect_task(user_input: str) -> str:
    lowered = user_input.lower()
    if "표" in user_input or "insight" in lowered:
        return "insight_extraction"
    if "공지" in user_input or "톤" in lowered:
        return "style_transfer"
    if "회의" in user_input or "보고" in user_input:
        return "summary_email"
    return "general_brief"


def compose_constraints(task_type: str) -> List[str]:
    constraints = [
        "제목은 1줄로 작성",
        "본문은 3~5문장으로 구성",
        "모든 문장은 존댓말로 작성",
        "과도한 확언/단정 금지",
    ]
    if task_type == "summary_email":
        constraints.append("Action items 2개 이상 포함")
    if task_type == "insight_extraction":
        constraints.append("핵심 인사이트 3~5개 불릿으로 정리")
    return constraints


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
    output_form = {
        "summary_email": "보고용 요약 이메일",
        "insight_extraction": "3~5개 불릿 인사이트",
        "style_transfer": "톤 변환 공지문",
        "general_brief": "간결한 비즈니스 요약",
    }.get(task, "간결한 비즈니스 요약")
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

    lowered = user_input.lower()
    llm_suggestions: List[str] = []
    updated_constraints = list(plan.constraints)

    if any(keyword in lowered for keyword in ["due", "deadline", "마감", "일정"]):
        llm_suggestions.append("마감과 담당자를 명시하라는 제약을 추가합니다.")
        updated_constraints.append("마감 일정과 담당자를 명확히 기재")

    if any(keyword in lowered for keyword in ["표", "table", "data", "%", "자료"]):
        llm_suggestions.append("숫자/데이터 근거를 표기하도록 요구합니다.")
        updated_constraints.append("숫자 근거를 함께 제시")

    if "친근" in user_input and plan.tone == "formal":
        llm_suggestions.append("요청에 맞게 친근한 톤으로 전환합니다.")
        tone = "friendly"
    else:
        tone = plan.tone

    requires_actions = any("action" in c.lower() for c in updated_constraints)
    if plan.task_type in {"summary_email", "general_brief"} and not requires_actions:
        llm_suggestions.append("후속 조치가 드러나도록 Action items 제약을 추가합니다.")
        updated_constraints.append("Action items 2개 이상 포함")

    # Deduplicate while preserving order
    seen = set()
    deduped_constraints = []
    for constraint in updated_constraints:
        if constraint not in seen:
            seen.add(constraint)
            deduped_constraints.append(constraint)

    coverage_score = min(1.0, 0.55 + 0.05 * len(deduped_constraints))
    confidence = round(min(1.0, plan.confidence * 0.9 + coverage_score * 0.2), 2)

    notes = " / ".join(llm_suggestions) if llm_suggestions else "LLM 검증: 주요 제약 충족 확인"

    return PlannerPlan(
        task_type=plan.task_type,
        output_form=plan.output_form,
        audience=plan.audience,
        tone=tone,
        constraints=deduped_constraints,
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
    sentences = re.split(r"[.!?\n]+", draft)
    sentence_count_ok = 3 <= len([s for s in sentences if s.strip()]) <= 6
    has_title = draft.startswith("제목:")
    tone_match = True  # Stubbed; real check would use model/NLP
    actions_present = "Action items" in draft or "Action" in draft
    concise = len(draft.split()) <= 180
    numbers_formatted = "%" in draft or bool(re.search(r"\d", draft))
    honorifics = any(word in draft for word in ["습니다", "드립니다", "해주세요"])
    avoids_overpromising = "확실" not in draft and "보장" not in draft
    failed: List[str] = []
    if not sentence_count_ok:
        failed.append("문장 수 3~5개 준수 필요")
    if not actions_present and "Action items" in plan.constraints:
        failed.append("Action items를 명시하세요")
    score = max(0.4, 1 - len(failed) * 0.1)
    return EvalReport(
        score=round(score, 2),
        checks=EvalCheck(
            has_title=has_title,
            sentence_count_ok=sentence_count_ok,
            tone_match=tone_match,
            actions_present=actions_present,
            concise=concise,
            numbers_formatted=numbers_formatted,
            honorifics=honorifics,
            avoids_overpromising=avoids_overpromising,
        ),
        suggestions=failed or ["전체적으로 요구사항을 충족했습니다."],
    )


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
