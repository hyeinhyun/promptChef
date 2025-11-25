from __future__ import annotations

"""Prompt composition utilities."""

from typing import List

from ..models import PlannerPlan, PromptSection
from ..utils.constraints import BUSINESS_TONES


_FEW_SHOT_EXAMPLES: dict[str, List[str]] = {
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


def build_few_shots(task_type: str) -> List[str]:
    return _FEW_SHOT_EXAMPLES.get(task_type, [])


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
