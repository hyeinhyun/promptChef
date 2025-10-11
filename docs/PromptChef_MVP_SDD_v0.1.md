# PromptChef — MVP SDD (Software Design Document) v0.1

작성일: 2025-10-11
범위: **프롬프트 추천 + 합성 + 결과 미리보기** (외부 API 실행 제외)

---

## 1. 개요 (Overview)

**PromptChef**는 AI 비전문가(일반 사무직)를 위해, 사용자의 목표를 해석하고 목적에 맞는 **프롬프트를 자동 합성**하여 **일관된 형식의 결과**를 미리보기로 제공하는 웹앱이다. 정적 템플릿 의존을 최소화하고, **에이전트 파이프라인(Planner→Composer→Evaluator→Refiner)**로 매 실행마다 적합한 프롬프트를 조립·검증·개선한다.

### 1.1 목표 (Goals)

* 사용자가 “무엇을 시켜야 할지” 고민하지 않게 **맞춤 프롬프트 추천/합성** 제공
* **한국 비즈니스 맥락**(격식/문체/형식)을 반영한 **재현성 높은 결과** 제공
* **앱 내부 미리보기**까지 지원 (외부 메일/문서 전송은 후속 단계)

### 1.2 비목표 (Non‑Goals)

* 외부 서비스(Gmail/Notion/Slack)로의 자동 발송/수행
* 개인화 모델 파인튜닝/자동학습 (MVP에서는 로깅 중심)
* 프롬프트 마켓/커뮤니티 기능

---

## 2. 사용자 및 요구사항

### 2.1 페르소나

* **일반 사무직**(마케팅/운영/기획/인사/CS): AI에 익숙하지 않음, 결과물 포맷 규범 중시

### 2.2 핵심 사용자 스토리

* S1: “회의 메모를 붙여넣으면, 상사 보고용 **요약 메일**을 바로 얻고 싶다.”
* S2: “엑셀 표 텍스트를 붙여넣으면 **핵심 인사이트** 3~5개가 필요하다.”
* S3: “공지문을 **톤만 바꿔**서 다시 쓰고 싶다(격식/친절/사과).”

### 2.3 기능 요구사항 (FR)

* FR1: 프로필(직무/톤/오늘 목표) 입력/저장
* FR2: **Planner**가 오늘의 작업 유형/출력 형식/톤/제약 추론
* FR3: **Composer**가 실행용 프롬프트 번들을 합성(System/User/Constraints/Few‑shot)
* FR4: **Runner**가 LLM 호출하여 결과 미리보기 제공
* FR5: **Evaluator**가 결과를 체크리스트로 평가(점수/개선 제안)
* FR6: **Refiner**가 평가 결과를 반영해 1회 보정(프롬프트/결과)
* FR7: 결과 저장/복사, 간단 피드백(👍/👎, 짧게/길게/톤) 로깅

### 2.4 비기능 요구사항 (NFR)

* NFR1: 평균 응답 5s 내(초기), 타임아웃 15s
* NFR2: 한국어 결과 가독성(문장 수/형식/존댓말) 일관성
* NFR3: 개인정보 최소 수집, 전송 구간 암호화(HTTPS), 토큰/로그 보호
* NFR4: 비용 가시화(토큰 사용량/호출 수 로깅)

---

## 3. 아키텍처

### 3.1 구성도(개요)

* **FE (Next.js, Tailwind, Zustand)**: 온보딩 → 입력폼 → 결과 패널/비교/피드백
* **BE (FastAPI, LangGraph)**: Planner → Composer → Runner → Evaluator → Refiner
* **DB (Supabase/Postgres)**: users, prompt_runs(계획/프롬프트/결과/로그)
* **LLM**: OpenAI GPT‑4‑mini(초기) / 로컬 vLLM(Qwen2.5 7B) 스파이크

### 3.2 에이전트 파이프라인

1. **Planner Agent**: 프로필/목표/히스토리 → `PlannerPlan`(task_type, output_form, tone, constraints, confidence)
2. **Prompt Composer**: `PlannerPlan`+사용자 입력 → `PromptBundle`(system, user, constraints, few_shot)
3. **Runner**: `PromptBundle` 실행 → `draft_output`
4. **Evaluator**: `bundle + draft` → `EvalReport(score, checks, suggestions)`
5. **Refiner**(1회): `bundle + draft + eval` → `final_prompt`, `final_output`

### 3.3 데이터 계약 (요약)

* **Profile**: role, interests[], today_goal, tone_pref, history?[]
* **PlannerPlan**: task_type, output_form, audience, tone, constraints, confidence, notes?
* **PromptBundle**: system, user, constraints, few_shot?[]
* **EvalReport**: score, checks{has_title, sent_len_ok, tone_match, actions_present, forbidden_phrases[]}, suggestions[]
* **Refined**: final_prompt{system,user,constraints}, final_output, change_notes[]

---

## 4. 상세 설계

### 4.1 Planner 설계

* 입력: Profile(today_goal 포함), 최근 run 로그(선택)
* 로직: 키워드/패턴 매칭 + 소형 LLM 분류 → task/output/tone/constraints 산출, confidence 계산
* 실패 처리: confidence≤0.6 → 대안 2안 생성(UX에서 선택)

### 4.2 Composer 설계

* 규칙: 한국 비즈니스 톤 정책(존댓말, 과도 확언 금지, 수치 괄호%) 포함
* 제약: 제목 1줄, 본문 3~5문장, Action items 포함 여부 등 **명시적 선언**
* Few‑shot: 태스크별 한국어 예시 1–2개 옵션 삽입(토큰/성능 트레이드오프)

### 4.3 Evaluator 설계

* 체크리스트(8항목): 제목/문장수/톤/액션/군더더기/수치 표기/존댓말/확언 금지
* 출력: score(0~1), failed 항목별 개선 제안 목록

### 4.4 Refiner 설계

* 전략: 실패 항목만 타깃팅, 1회 재시도(토큰 절약)
* 산출: 최종 프롬프트/최종 결과 + 변경 로그(`change_notes`)

### 4.5 Runner/비용 관리

* 토큰 상한, 타임아웃, 캐시(입력 해시 5~15분) 적용
* `prompt_runs`에 in/out 토큰/지연시간 로깅

---

## 5. 데이터 모델 (초안)

* `users(id, email, role, tone_pref, created_at)`
* `prompt_runs(id, user_id, plan jsonb, bundle jsonb, preview text, rating int, tokens_in int, tokens_out int, latency_ms int, created_at)`
  Row Level Security: 사용자 본인만 접근

---

## 6. API 설계 (MVP)

**POST `/compose_and_run`**
Request: `{ profile: Profile, user_input: string }`
Response: `{ plan, bundle, preview (or final_output), meta{tokens, latency_ms} }`

보조 엔드포인트:

* `GET /healthz`
* `POST /feedback` (run_id, rating, actions["shorter","longer","tone_formal"...])

---

## 7. UX 플로우

1. 온보딩: 직무/톤/오늘 목표 입력 저장
2. 작성 화면: 목표 1줄 + 원문 붙여넣기 → **Run**
3. 결과 패널: 초안 vs 개선본 탭, 복사/북마크, 빠른 리파인(짧게/길게/톤)
4. 피드백 제출: 👍/👎 및 선택 사유 → 다음 추천 가중치에 반영(후속)

---

## 8. 보안/개인정보

* 최소 수집: 이메일/역할/톤/입력 텍스트(운영상 필요한 범위)
* 전송 암호화: HTTPS, 서버측 비밀키 .env 관리
* RLS 정책으로 사용자 데이터 격리
* 로그 보존 기간 MVP 단계 단축(예: 30일) 후정책 명시

---

## 9. 모니터링/지표

* 제품 지표: 실행수/인당 세션당 실행률, 결과 복사율, 👍율, 7일 재방문율
* 기술 지표: 평균 지연, 95p 지연, 오류율, 토큰/유저/일
* 품질 지표(에이전트): 합성적중률, 자체심사 통과율, 수정요청율

---

## 10. 릴리즈/배포

* 로컬: Docker Compose(FE/BE/DB)
* 스테이징: Vercel(FE) + Railway/Render(BE) + Supabase(DB)
* 환경: `dev`/`stg`/`prod` 분리, 기본 헬스체크 및 rate limit

---

## 11. 리스크 & 대응

* LLM 비용/지연: 캐시/상한/타임아웃, 짧은 프롬프트 설계, few‑shot 최소화
* 한국어 톤 품질: 정책 강화 + Evaluator 체크리스트 정교화
* 의도 파싱 오인식: confidence 기반 대안안 제시 및 UX 선택

---

## 12. 로드맵(요약)

* **Week 1**: 아키텍처/스키마/스켈레톤, Mock 기반 E2E 스모크
* **Week 2**: Planner/Composer/Runner 연결, 최초 합성 실행
* **Week 3**: Evaluator/Refiner 통합, 결과 비교/피드백 UX
* **Week 4**: 품질/성능/배포/로깅/지표 세팅

---

## 13. 오픈 이슈

* Evaluator 체크리스트 항목 가중치(동등? 중요도 차등?)
* Few‑shot 동적 삽입 기준(태스크별 or 실패율 기반)
* vLLM 로컬 모델 전환 시의 품질/지연/비용 트레이드오프

