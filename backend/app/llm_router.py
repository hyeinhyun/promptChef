"""LLM Provider 라우팅. brain(fast/deep) × provider(openai/google) 조합."""

import time
from app.config import settings
from app.models import BrainTier, Provider


class LLMError(RuntimeError):
    pass


def _resolve_model(provider: Provider, brain: BrainTier) -> str:
    if provider == "openai":
        return settings.fast_model_openai if brain == "fast" else settings.deep_model_openai
    return settings.fast_model_google if brain == "fast" else settings.deep_model_google


def _resolve_provider(requested: Provider | None) -> Provider:
    """요청 > 기본 설정 > 키가 있는 공급자 순으로 결정. 어느 것도 없으면 LLMError."""
    openai_ready = bool(settings.openai_api_key)
    google_ready = bool(settings.google_api_key)

    if requested:
        if requested == "openai" and not openai_ready:
            raise LLMError("OPENAI_API_KEY가 설정되지 않았습니다.")
        if requested == "google" and not google_ready:
            raise LLMError("GOOGLE_API_KEY가 설정되지 않았습니다.")
        return requested

    preferred = settings.default_provider if settings.default_provider in ("openai", "google") else "openai"
    if preferred == "openai" and openai_ready:
        return "openai"
    if preferred == "google" and google_ready:
        return "google"
    # 선호값 키가 없으면 다른 쪽으로 fallback.
    if openai_ready:
        return "openai"
    if google_ready:
        return "google"
    raise LLMError("OPENAI_API_KEY 또는 GOOGLE_API_KEY 중 최소 하나는 설정되어야 합니다.")


async def generate(
    system_prompt: str,
    user_input: str,
    brain: BrainTier,
    provider: Provider | None = None,
) -> tuple[str, dict]:
    """프롬프트 생성. 반환: (text, meta)."""
    chosen_provider = _resolve_provider(provider)
    model = _resolve_model(chosen_provider, brain)
    started = time.perf_counter()

    if chosen_provider == "openai":
        text = await _call_openai(model, system_prompt, user_input)
    else:
        text = await _call_google(model, system_prompt, user_input)

    latency_ms = int((time.perf_counter() - started) * 1000)
    return text, {"provider": chosen_provider, "model": model, "latency_ms": latency_ms}


async def _call_openai(model: str, system_prompt: str, user_input: str) -> str:
    if not settings.openai_api_key:
        raise LLMError("OPENAI_API_KEY가 설정되지 않았습니다.")
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
        temperature=0.7,
    )
    content = resp.choices[0].message.content
    if not content:
        raise LLMError("OpenAI가 빈 응답을 반환했습니다.")
    return content.strip()


async def _call_google(model: str, system_prompt: str, user_input: str) -> str:
    if not settings.google_api_key:
        raise LLMError("GOOGLE_API_KEY가 설정되지 않았습니다.")
    import google.generativeai as genai

    genai.configure(api_key=settings.google_api_key)
    gm = genai.GenerativeModel(model_name=model, system_instruction=system_prompt)
    resp = await gm.generate_content_async(user_input)
    text = (resp.text or "").strip()
    if not text:
        raise LLMError("Gemini가 빈 응답을 반환했습니다.")
    return text
