from __future__ import annotations

"""Pipeline orchestration services."""

import random
import time

from ..core.composer import composer
from ..core.evaluator import evaluate
from ..core.planner import planner
from ..core.refiner import refine
from ..core.runner import runner
from ..models import (
    AutoComposeResponse,
    ComposeAndPlanRequest,
    ComposeAndPlanResponse,
    ComposeAndRunRequest,
    ComposeAndRunResponse,
    EvalReport,
    PlannerPlan,
    PromptBundle,
    RunMeta,
    RunWithRefineResponse,
)
from ..utils.constraints import adjust_confidence, dedupe_preserve_order


def compose_with_plan(
    plan: PromptBundle | PlannerPlan, user_input: str, *, start: float | None = None
) -> ComposeAndRunResponse:
    """Legacy helper that runs end-to-end with a provided plan or bundle."""

    timer_start = start if start is not None else time.time()
    bundle = plan if isinstance(plan, PromptBundle) else PromptBundle(plan=plan, sections=composer(plan, user_input))
    draft_output = runner(bundle.sections)
    eval_report = evaluate(draft_output, bundle.plan)
    final_output = refine(draft_output, eval_report)
    elapsed_ms = int((time.time() - timer_start) * 1000)
    tokens_in = len(bundle.sections.user.split()) + len(bundle.sections.system.split())
    tokens_out = len(final_output.split())
    meta = RunMeta(tokens_in=tokens_in, tokens_out=tokens_out, latency_ms=elapsed_ms)
    return ComposeAndRunResponse(
        plan=bundle.plan,
        bundle=bundle,
        preview=draft_output,
        final_output=final_output,
        meta=meta,
    )


def compose_and_run(request: ComposeAndRunRequest) -> ComposeAndRunResponse:
    plan = planner(request)
    bundle = PromptBundle(plan=plan, sections=composer(plan, request.user_input))
    run_response = run_with_refine(bundle)
    return ComposeAndRunResponse(
        plan=plan,
        bundle=bundle,
        preview=run_response.draft or "",
        final_output=run_response.final_output,
        meta=run_response.meta,
    )


def compose_and_plan(request: ComposeAndPlanRequest) -> ComposeAndPlanResponse:
    plan = planner(request)
    bundle = PromptBundle(plan=plan, sections=composer(plan, request.user_input))
    return ComposeAndPlanResponse(plan=plan, bundle=bundle)


def run_with_refine(bundle: PromptBundle) -> RunWithRefineResponse:
    timer_start = time.time()
    draft_output = runner(bundle.sections)
    eval_report = evaluate(draft_output, bundle.plan)
    final_output = refine(draft_output, eval_report)
    elapsed_ms = int((time.time() - timer_start) * 1000)
    tokens_in = len(bundle.sections.user.split()) + len(bundle.sections.system.split())
    tokens_out = len(final_output.split())
    meta = RunMeta(tokens_in=tokens_in, tokens_out=tokens_out, latency_ms=elapsed_ms)

    return RunWithRefineResponse(
        final_output=final_output,
        eval_meta=eval_report,
        meta=meta,
        draft=draft_output,
    )


def _augment_plan_with_feedback(plan: PlannerPlan, report: EvalReport) -> PlannerPlan:
    added_constraints = [f"재시도: {suggestion}" for suggestion in report.suggestions]
    constraints = dedupe_preserve_order(plan.constraints + added_constraints)
    new_confidence = adjust_confidence(plan.confidence, constraints)
    notes = (plan.notes or "").strip()
    notes = f"{notes} / 평가 반영" if notes else "평가 피드백 반영"
    return PlannerPlan(
        task_type=plan.task_type,
        output_form=plan.output_form,
        audience=plan.audience,
        tone=plan.tone,
        constraints=constraints,
        confidence=new_confidence,
        notes=notes,
    )


def auto_compose_and_run(
    request: ComposeAndRunRequest, *, max_rounds: int = 3, target_score: float = 0.85
) -> AutoComposeResponse:
    evaluations: list[EvalReport] = []
    current_plan = planner(request)
    response = compose_with_plan(current_plan, request.user_input)
    evaluations.append(evaluate(response.preview, response.plan))

    attempts = 1
    while attempts < max_rounds and evaluations[-1].score < target_score:
        current_plan = _augment_plan_with_feedback(response.plan, evaluations[-1])
        response = compose_with_plan(current_plan, request.user_input)
        evaluations.append(evaluate(response.preview, response.plan))
        attempts += 1

    return AutoComposeResponse(final=response, evaluations=evaluations)


def save_feedback(feedback_id: str, rating: int, actions: list[str]) -> None:
    random.seed(feedback_id)
    _ = random.random()
    return None
