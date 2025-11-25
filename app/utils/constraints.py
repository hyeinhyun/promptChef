from __future__ import annotations

"""Constraint helpers and shared configuration constants."""

from typing import Iterable, List, Sequence, Set, Tuple

BUSINESS_TONES: dict[str, str] = {
    "formal": "격식 있고 간결한 존댓말",
    "friendly": "친근하지만 예의 있는 톤",
    "apology": "정중한 사과 톤",
}

TASK_KEYWORDS: dict[str, Set[str]] = {
    "insight_extraction": {"표", "insight"},
    "style_transfer": {"공지", "톤"},
    "summary_email": {"회의", "보고"},
}

TASK_OUTPUT_FORMS: dict[str, str] = {
    "summary_email": "보고용 요약 이메일",
    "insight_extraction": "3~5개 불릿 인사이트",
    "style_transfer": "톤 변환 공지문",
    "general_brief": "간결한 비즈니스 요약",
}

BASE_CONSTRAINTS: List[str] = [
    "제목은 1줄로 작성",
    "본문은 3~5문장으로 구성",
    "모든 문장은 존댓말로 작성",
    "과도한 확언/단정 금지",
]

TASK_CONSTRAINTS: dict[str, List[str]] = {
    "summary_email": ["Action items 2개 이상 포함"],
    "insight_extraction": ["핵심 인사이트 3~5개 불릿으로 정리"],
}

CONSTRAINT_HINTS: Sequence[Tuple[Set[str], str, str]] = (
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


def dedupe_preserve_order(items: Iterable[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def adjust_confidence(base_confidence: float, constraints: Sequence[str]) -> float:
    coverage_score = min(1.0, 0.55 + 0.05 * len(constraints))
    return round(min(1.0, base_confidence * 0.9 + coverage_score * 0.2), 2)
