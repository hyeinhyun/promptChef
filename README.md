# My Office Mate

AI에 익숙하지 않은 직장인이 자연어만으로 고도화된 프롬프트를 만들 수 있도록 돕는 크롬 익스텐션 + FastAPI 백엔드.

> "사내 동료(메이트)"가 옆자리에서 도와주는 느낌의 친근한 UI. 결과물에 만족하면 메이트의 인사고과(레벨)가 올라간다.

## 컨셉
- **타겟**: 마케터/기획자/영업 등 일반 사무직, AI 비숙련 사용자.
- **차별점**:
  1. AI 용어 배제(프롬프트/모델/토큰 같은 단어 노출 최소화).
  2. 3종 메이트 페르소나 — 꼼꼼한 사수 / 싹싹한 동기 / 엉뚱한 인턴.
  3. 결재 완료(복사) 클릭 시 EXP 적립 → 레벨업(수습 → 대리 → 팀장).

## 개발 일정
2026-04-22(수) ~ 2026-04-24(금) — 3일 스프린트.

## 시스템 아키텍처
```
[Chrome Extension MV3]
  ├─ popup/        자연어 입력 + 결과 카드 + EXP 게이지
  ├─ onboarding/   닉네임 + 메이트 선택
  └─ chrome.storage.local  (유저/EXP/레벨 저장)
        │
        │ HTTPS (ngrok 터널)
        ▼
[FastAPI Backend]
  ├─ /generate           페르소나별 시스템 프롬프트 조립 + LLM Inference
  ├─ /personas           페르소나 메타 반환
  └─ LLM Router          fast(GPT-4o-mini / Gemini Flash) | deep(GPT-4o / Gemini Pro)
```

## 기술 스택
**Frontend (Chrome Extension)**
- Manifest V3, Vanilla JS, HTML, 정적 CSS (`extension/styles/app.css` — Tailwind 스타일의 유틸리티 클래스. MV3 CSP 때문에 CDN 미사용.)
- 상태: `chrome.storage.local` (별도 DB 없음)

**Backend**
- Python 3.11+, FastAPI, Pydantic
- 패키지: `uv`
- LLM: `openai`, `google-generativeai`
- 배포: `ngrok` 임시 터널

## 실행 방법

### 1. 백엔드
```bash
cd backend
uv venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv sync

# 환경변수
cp .env.example .env        # OPENAI_API_KEY, GOOGLE_API_KEY 채우기

# 서버 실행
uv run uvicorn app.main:app --reload --port 8000

# (옵션) ngrok 터널
ngrok http 8000
```

### 2. 익스텐션 로드
1. Chrome → `chrome://extensions` 진입.
2. "개발자 모드" 토글 ON.
3. "압축해제된 확장 프로그램을 로드합니다" → `extension/` 폴더 선택.
4. 익스텐션 옵션에서 백엔드 URL 입력 (기본: `http://localhost:8000`).

## 폴더 구조
```
backend/
  app/
    main.py          FastAPI 엔드포인트
    personas.py      메이트 3종 시스템 프롬프트
    llm_router.py    OpenAI / Gemini 라우팅
    models.py        Pydantic 스키마
    config.py        설정 로드
  pyproject.toml
  .env.example

extension/
  manifest.json
  popup/             메인 UI (자연어 입력 + 결과)
  onboarding/        초기 1회 설정
  options/           백엔드 URL 등 설정
  lib/               storage / api / exp 헬퍼
  assets/            아이콘 + 캐릭터 SVG
```

## API 계약
### POST `/generate`
요청:
```json
{
  "user_input": "다음 주 캠페인 회의 준비 자료 만들어줘",
  "persona": "senior",        // senior | peer | intern
  "brain": "fast",            // fast | deep
  "nickname": "현이"
}
```
응답:
```json
{
  "prompt": "당신은 ...\n\n# 작업\n...\n\n# 출력 형식\n...",
  "meta": {
    "persona": "senior",
    "brain": "fast",
    "model": "gpt-4o-mini",
    "latency_ms": 842
  }
}
```

### GET `/personas`
3종 메이트 메타 반환 (id, 이름, 설명, 톤 키워드).
