from __future__ import annotations

"""Prompt composition utilities."""

from typing import List

from ..models import PlannerPlan, PromptSection
from ..prompts import FEW_SHOT_EXAMPLES, SYSTEM_PROMPT_TEMPLATE, USER_PROMPT_TEMPLATE
from ..utils.constraints import BUSINESS_TONES


def build_few_shots(task_type: str) -> List[str]:
    return FEW_SHOT_EXAMPLES.get(task_type, [])


def build_system_prompt(task_type: str, tone: str) -> str:
    tone_desc = BUSINESS_TONES.get(tone, BUSINESS_TONES["formal"])
    return SYSTEM_PROMPT_TEMPLATE.format(tone_desc=tone_desc)


def build_user_prompt(user_input: str, plan: PlannerPlan) -> str:
    constraints = ", ".join(plan.constraints)
    return USER_PROMPT_TEMPLATE.format(
        task_type=plan.task_type,
        output_form=plan.output_form,
        audience=plan.audience,
        constraints=constraints,
        user_input=user_input.strip(),
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
