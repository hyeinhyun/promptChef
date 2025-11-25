from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .models import (
    ComposeAndPlanRequest,
    ComposeAndRunRequest,
    FeedbackRequest,
    RunWithRefineRequest,
)
from .services.pipeline_service import compose_and_plan, compose_and_run, run_with_refine, save_feedback

app = FastAPI(title="PromptChef MVP API", version="0.1")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/compose_and_run")
def compose_and_run_endpoint(payload: ComposeAndRunRequest):
    return compose_and_run(payload)


@app.post("/compose_and_plan")
def compose_and_plan_endpoint(payload: ComposeAndPlanRequest):
    return compose_and_plan(payload)


@app.post("/run_with_refine")
def run_with_refine_endpoint(payload: RunWithRefineRequest):
    return run_with_refine(payload.bundle)


@app.post("/feedback")
def feedback(payload: FeedbackRequest) -> dict[str, str]:
    try:
        save_feedback(payload.run_id, payload.rating, payload.actions)
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"status": "received"}
