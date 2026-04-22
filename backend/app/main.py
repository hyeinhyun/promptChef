from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.llm_router import LLMError, generate
from app.models import (
    GenerateMeta,
    GenerateRequest,
    GenerateResponse,
    PersonasResponse,
)
from app.personas import list_personas, system_prompt_for

app = FastAPI(title="My Office Mate API", version="0.1.0")

origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()] or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}


@app.get("/personas", response_model=PersonasResponse)
def get_personas() -> PersonasResponse:
    return PersonasResponse(personas=list_personas())


@app.post("/generate", response_model=GenerateResponse)
async def post_generate(req: GenerateRequest) -> GenerateResponse:
    system_prompt = system_prompt_for(req.persona, req.nickname)
    try:
        text, meta = await generate(
            system_prompt=system_prompt,
            user_input=req.user_input,
            brain=req.brain,
            provider=req.provider,
        )
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return GenerateResponse(
        prompt=text,
        meta=GenerateMeta(
            persona=req.persona,
            brain=req.brain,
            provider=meta["provider"],
            model=meta["model"],
            latency_ms=meta["latency_ms"],
        ),
    )
