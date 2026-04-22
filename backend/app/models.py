from typing import Literal, Optional
from pydantic import BaseModel, Field


PersonaId = Literal["senior", "peer", "intern"]
BrainTier = Literal["fast", "deep"]
Provider = Literal["openai", "google"]


class GenerateRequest(BaseModel):
    user_input: str = Field(..., min_length=1, max_length=4000)
    persona: PersonaId = "senior"
    brain: BrainTier = "fast"
    provider: Optional[Provider] = None
    nickname: Optional[str] = None


class GenerateMeta(BaseModel):
    persona: PersonaId
    brain: BrainTier
    provider: Provider
    model: str
    latency_ms: int


class GenerateResponse(BaseModel):
    prompt: str
    meta: GenerateMeta


class PersonaInfo(BaseModel):
    id: PersonaId
    name: str
    title: str
    description: str
    tone_keywords: list[str]
    emoji: str


class PersonasResponse(BaseModel):
    personas: list[PersonaInfo]
