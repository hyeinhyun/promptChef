from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Profile(BaseModel):
    role: Optional[str] = Field(None, description="사용자의 직무")
    interests: List[str] = Field(default_factory=list, description="관심 주제 리스트")
    today_goal: Optional[str] = Field(None, description="오늘의 목표")
    tone_pref: Optional[str] = Field(None, description="선호 톤")
    history: List[str] = Field(default_factory=list, description="최근 실행 로그 요약")


class PlannerPlan(BaseModel):
    task_type: str
    output_form: str
    audience: str
    tone: str
    constraints: List[str]
    confidence: float = Field(ge=0.0, le=1.0)
    notes: Optional[str] = None


class PromptSection(BaseModel):
    system: str
    user: str
    constraints: List[str]
    few_shot: List[str]


class PromptBundle(BaseModel):
    plan: PlannerPlan
    sections: PromptSection


class EvalCheck(BaseModel):
    has_title: bool
    sentence_count_ok: bool
    tone_match: bool
    actions_present: bool
    concise: bool
    numbers_formatted: bool
    honorifics: bool
    avoids_overpromising: bool


class EvalReport(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    checks: EvalCheck
    suggestions: List[str]


class RunMeta(BaseModel):
    tokens_in: int
    tokens_out: int
    latency_ms: int


class ComposeAndRunRequest(BaseModel):
    profile: Profile
    user_input: str


class ComposeAndRunResponse(BaseModel):
    plan: PlannerPlan
    bundle: PromptSection
    preview: str
    final_output: str
    meta: RunMeta


class FeedbackRequest(BaseModel):
    run_id: str
    rating: int = Field(..., ge=1, le=5)
    actions: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
