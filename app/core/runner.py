from __future__ import annotations

"""Draft generation runner."""

from ..models import PromptSection


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
