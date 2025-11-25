from __future__ import annotations

"""Central prompt templates for prompt composition."""

SYSTEM_PROMPT_TEMPLATE = (
    "당신은 한국 비즈니스 글쓰기 어시스턴트입니다. "
    "톤: {tone_desc}. 출력 형식을 반드시 준수하고 불필요한 장식을 피하세요."
)

USER_PROMPT_TEMPLATE = (
    "요청 유형: {task_type}\n"
    "출력 형식: {output_form}\n"
    "대상: {audience}\n"
    "추가 제약: {constraints}\n"
    "원문:\n{user_input}"
)

FEW_SHOT_EXAMPLES: dict[str, list[str]] = {
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
