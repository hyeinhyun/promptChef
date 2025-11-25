from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .models import ComposeAndRunRequest, FeedbackRequest
from .services.pipeline_service import compose_and_run, save_feedback

app = FastAPI(title="PromptChef MVP API", version="0.1")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/compose_and_run")
def compose_and_run_endpoint(payload: ComposeAndRunRequest):
    return compose_and_run(payload)


@app.post("/feedback")
def feedback(payload: FeedbackRequest) -> dict[str, str]:
    try:
        save_feedback(payload.run_id, payload.rating, payload.actions)
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"status": "received"}
