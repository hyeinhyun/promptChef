# PromptChef MVP API

PromptChef는 한국 비즈니스 맥락에 맞춰 프롬프트를 계획·합성·평가·보정하여 미리보기를 제공하는 실험용 FastAPI 서비스입니다. 이 리포지토리는 외부 LLM 없이 동작하는 MVP 스켈레톤을 포함합니다.

## 주요 구성
- `app/main.py`: FastAPI 엔드포인트(`/compose_and_run`, `/feedback`, `/healthz`).
- `app/pipeline.py`: Planner → Composer → Runner → Evaluator → Refiner 파이프라인을 간단한 규칙 기반으로 구현.
- `app/models.py`: 프로필, 플랜, 번들, 평가 리포트, 실행 메타데이터에 대한 Pydantic 모델.

## 실행 방법
uv(https://docs.astral.sh/uv/)으로 가상환경과 의존성을 관리하며, 필요한 패키지는 `pyproject.toml`에 정의되어 있습니다.

```bash
# uv가 없다면 설치
curl -LsSf https://astral.sh/uv/install.sh | sh

# 프로젝트 의존성 설치
uv venv
source .venv/bin/activate
uv sync

# 개발 서버 실행 (API가 필요할 때만)
uv run uvicorn app.main:app --reload --port 8000

# CLI에서 직접 파이프라인 실행
uv run promptchef compose_and_run \
  --data '{"profile": {"role": "마케팅 매니저", "tone_pref": "formal"}, "user_input": "회의 메모: 신규 캠페인"}'

# 또는 파일로 요청 전달 (stdin도 지원)
uv run promptchef /compose_and_run --file payload.json --pretty
```

## 사용 예시
### 2단계 API 흐름 (MVP 사양 반영)

1. **/compose_and_plan** — Planner + Composer (LLM Call #1)

```bash
curl -X POST http://localhost:8000/compose_and_plan \
  -H "Content-Type: application/json" \
  -d '{
    "profile": {"role": "마케팅 매니저", "today_goal": "주간 보고", "tone_pref": "formal"},
    "user_input": "회의 메모: 신규 캠페인 CTR 12% 개선, 예산 5% 상향 요청"
  }'
```

응답: `{ "plan": PlannerPlan, "bundle": { "plan": ..., "sections": {system, user, constraints, few_shot} } }`

2. **/run_with_refine** — Runner + Self-Evaluator + Refiner (LLM Call #2)

```bash
curl -X POST http://localhost:8000/run_with_refine \
  -H "Content-Type: application/json" \
  -d '{ "bundle": { ...compose_and_plan에서 반환된 번들... } }'
```

응답: 최종 결과(`final_output`), 평가 메타(`eval_meta`), 초안(`draft`), 토큰/지연 메타(`meta`).

기존 단일 `/compose_and_run` 엔드포인트도 계속 제공되며 두 단계를 내부에서 순차 실행합니다.
