from __future__ import annotations

"""Pipeline orchestration services."""

import random
import time

from ..core.composer import composer
from ..core.evaluator import evaluate
from ..core.planner import planner
from ..core.refiner import refine
from ..core.runner import runner
from ..models import AutoComposeResponse, ComposeAndRunRequest, ComposeAndRunResponse, EvalReport, PlannerPlan, RunMeta
from ..utils.constraints import adjust_confidence, dedupe_preserve_order


def compose_with_plan(plan: PlannerPlan, user_input: str, *, start: float | None = None) -> ComposeAndRunResponse:
    timer_start = start if start is not None else time.time()
    bundle = composer(plan, user_input)
    draft_output = runner(bundle)
    eval_report = evaluate(draft_output, plan)
    final_output = refine(draft_output, eval_report)
    elapsed_ms = int((time.time() - timer_start) * 1000)
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


def compose_and_run(request: ComposeAndRunRequest) -> ComposeAndRunResponse:
    return compose_with_plan(planner(request), request.user_input, start=time.time())


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
