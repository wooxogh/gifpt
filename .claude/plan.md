# GIFPT Measurement-Driven Refactor — 실행 플랜

> **기준 문서:** `gifpt-measurement-driven-refactor.md` (canonical)
> **이 문서의 역할:** canonical의 설계를 **주차별 체크리스트**로 번역. 매일 열어보는 실행 문서.
> **사용법:** 완료 시 `[x]` 체크. 각 주 말 DoW(Definition of Week) 통과 여부 확인 후 다음 주로 넘어감.
> **총 기간:** 6주 (+ 버퍼 2주) — 기존 15주 플랜에서 축소. 축소 이유는 `docs/build-vs-buy-spike.md`.

---

## Gate 요약

| Gate | 시점 | 조건 | 실패 시 |
|---|---|---|---|
| **Gate 0** | ✅ 완료 | Build-vs-Buy 스파이크 결과 = LangSmith 채택, 자체 빌드 폐기 | — |
| **Gate 1** | Week 1 말 | Phase 0 3 문서 사용자 승인 + LangSmith goldset v0 업로드 | Phase 1 착수 금지, Phase 0 연장 |
| **Gate 2** | Week 3 말 | 실험 A 수치 벡터 (pass rate × cost × latency × judge) 존재 | Phase 2 연기, evaluator 디버그 |
| **Gate 3** | Week 5 말 | Judge self-calibration agreement ≥ 85% + 실험 B diff | Rubric 재튜닝, Week 6 1주 연기 |
| **Gate 4** | Week 6 말 | 블로그 draft 1 + 이력서 update + 면접 pitch 완성 | 버퍼 주로 이월 |

---

## Day 0 — Build-vs-Buy 스파이크 ✅ 완료 (2026-04-12)

**결과 요약:** 자체 Harness CI 빌드 폐기. LangSmith + custom code evaluator 4개로 edge preservation 측정. 자세한 내용은 `gifpt/docs/build-vs-buy-spike.md`.

Narrative는 "내가 도구를 만들었다"에서 **"측정 기반으로 내 시스템을 고쳤다"**로 전환.

---

## Day 1 — 열린 결정사항 ✅ 확정 (2026-04-12)

- [x] **A. GIFPT v2 Agent SDK:** **Claude Agent SDK** — 단일 agentic loop + 5 tools
- [x] **B. Goldset 확장 시점:** **Week 3** — 실험 A 이후 16 → 36 case 승격
- [x] **C. Judge golden 20개 제공 시점:** **Week 4** — v2 스캐폴드 완성 직후, calibration 직전
- [x] **D. v2 default route 스위칭 기준:** **Edge preservation fail rate −30% 이상**
- [ ] E. Blog 공개 시점 — Week 6 말 도달 후 결정 (연기)

---

## Phase 0 — Narrative 산출물 + LangSmith 셋업 (Week 1)

> **제약:** 새 코드 금지 (LangSmith 세팅 외). GIFPT 리포 `docs/`에만 commit.

### Week 1 — 3 문서 + 골든셋 + LangSmith 환경

**산출물 1:** `gifpt/docs/failure-taxonomy.md` ✅

- [x] `scripts/failure_audit.py` 재실행 + 결과 저장 (reports/failure_audit_2026-04-09.md)
- [x] `scripts/weekly_audit.py` 최근 로그 20개 수동 검토
- [x] 기존 6-stage taxonomy를 **edge 원인**으로 재분류
- [x] 각 failure class에 edge 매핑 표 작성 (`pseudo→anim`, `anim→codegen`, `codegen→render`, `render→qa`)
- [x] 실패 8건 각각에 edge 원인 라벨

**산출물 2:** `gifpt/docs/v1-baseline-report.md` ✅

- [x] `seed_audit.py` 재실행 (16 seed × 전체 stage)
- [x] 16 케이스별 stage pass/fail 표
- [x] Failure class 분포 차트 (taxonomy 기준)
- [x] Edge preservation 증거 4개 수동 카운트:
  - [x] `_UNKNOWN_HELPERS` (11개) — `llm_codegen.py:427`
  - [x] LSM-Tree 오분류 주석 — `video_render.py:311`
  - [x] `sorting.comparison_shown -2.5` 페널티 — `qa.py:281`
  - [x] `_INVALID_COLOR_MAP` (15개) — `llm_codegen.py:409` → **실제 26 regex rules** (15 color + 11 helper)
- [x] baseline 4차원 벡터 (pass/cost/latency/judge) 한 장 요약

**산출물 3:** `gifpt/docs/edge-first-measurement.md` ✅

- [x] Axiom 3개 정리 (delta / edge-first / dynamic graph)
- [x] Edge 증거 4개 표
- [x] `scripts/README.md:103-104` 인용문 앵커
- [x] Delta vs quality 철학 섹션
- [x] 경쟁 지형 표 (promptfoo / Inspect AI / LangSmith / Weave — build-vs-buy 결과 반영)
- [x] LangSmith 선택 근거 + custom evaluator 4개 설계

**LangSmith 셋업:** ✅

- [x] LangSmith 계정 생성 + API key 발급
- [x] `pip install langsmith` + `LANGSMITH_*` 환경 변수 + `requirements.txt` 반영
- [x] GIFPT 파이프라인에 `@traceable` 데코레이터 주입 (5지점: pseudo_ir, anim_ir, codegen, render, qa)
- [x] Safe fallback helper 구성 (`studio/ai/_tracing.py`) — langsmith 미설치 시 no-op
- [x] **Goldset v0 업로드** — `seed_examples.jsonl` (16 case) → LangSmith Dataset `gifpt-goldset-v0` (id=75f5e777-99e6-4914-97a8-0be3b696f4f8)
- [x] pytest 격리 (`pytest.ini` + `requirements-dev.txt`)

**Week 1 말 Gate 1 체크:**

- [x] `failure-taxonomy.md` self-review ✅ (user review 대기)
- [x] `v1-baseline-report.md` self-review ✅ (user review 대기)
- [x] `edge-first-measurement.md` self-review ✅ (user review 대기)
- [x] LangSmith goldset v0 업로드 완료
- [ ] GIFPT 파이프라인 trace 1건 이상 LangSmith UI에 표시 (Week 2 실 실행 시 확인)
- [x] **면접 Ready 라인 1 확보** — 위 3 문서만으로 narrative 성립 self-check

**Gate 1 통과 시** → Phase 1 Week 2 착수
**Gate 1 실패 시** → 문서 보완 후 재review

---

## Phase 1 — LangSmith Custom Evaluator + 실험 A (Week 2-3)

### Week 2 — 4 Custom Evaluator 구현

**산출물:** `GIFPT_AI/studio/evaluators/` (`gifpt/evaluators/`에서 위치 조정 — import 경로 정합)

- [x] `base.py` — `EdgeEvalResult` 공통 반환 타입 + LangSmith feedback 어댑터
- [x] `pseudo_anim_preservation.py`
  - [x] Pseudo IR entity/operation set → Anim IR layout/action 보존 여부
  - [x] Pass/fail + 누락 항목 리스트 반환
- [x] `anim_codegen_preservation.py`
  - [x] Anim IR layout id → Manim 코드 AST 존재 여부
  - [x] AST 기반 hallucinated helper + forbidden API 검출 (`_UNKNOWN_HELPERS` / `FORBIDDEN_NAMES`)
- [x] `codegen_render_preservation.py`
  - [x] `validate_manim_code_ast` forbidden AST 검출 재사용
  - [x] 렌더 success/duration/timeout budget (180s)
- [x] `render_qa_preservation.py`
  - [x] Vision QA score + passed 판정
  - [x] `DOMAIN_QA_CONFIG` required_checks 미달 플래그
- [x] 각 evaluator에 단위 테스트 1개 이상 (known good/bad case) — **20 tests, 20 passed**
- [x] `pipeline_capture.py` — 1-shot 파이프라인 러너 (retry 없이 first-try 측정)
- [x] `langsmith_adapter.py` — 4 evaluator를 LangSmith `(run, example) → feedback` 시그니처로 랩핑
- [x] `scripts/run_evaluators_baseline.py` — CLI runner (`--offline` / `--dry-run` / live modes)
- [x] Offline smoke test 통과 — 4/4 evaluator × 1 fixture case 모두 PASS
- [x] LangSmith live baseline run — Week 3 Task 6에서 실행 완료
- [x] Edge fail 카운트가 baseline 리포트 숫자와 일치 확인 — FULL session `b4315c13` 집계

**DoW:** 4 evaluator 모듈 + 단위 테스트 + LangSmith wiring + CLI 전부 존재, offline smoke PASS.
**실제 16 case × 4 evaluator 매트릭스는 Week 3 Phase 1 실험 A에서 수집.**

### Week 3 — 실험 A (Prompt 감량) + Gate 2

- [x] **Baseline run**: `PEDAGOGICAL_RULES_FULL` × goldset v0 (16 case) — session `b4315c13-7e06-4acf-a6fc-1e6ccfbe5722`
  - [x] 4차원 벡터 기록: render 81.2% / $0.8713 / 34.3s / QA 5.78 / edges [0.50, 0.50, 0.625, 0.6875]
- [x] **실험 A run**: `PEDAGOGICAL_RULES_CONDENSED` × goldset v0 (16 case) — session `f0a1de2b-1bd7-4bd2-8c5f-1c4c468f4059`
  - [x] 같은 4차원 벡터 기록: render 68.8% / $0.8540 / 43.7s / QA 4.64 / edges [0.6875, 0.6875, 0.625, 0.625]
- [x] LangSmith run diff UI로 "X green, Y red, cost -Z%" 확인 — pseudo_anim +18.8%p, anim_codegen +18.8%p, render_qa −6.25%p, cost −2%
- [x] 수치 박제: `docs/snapshots/experiment-a-prompt-tweak.md`
  - [x] 원인 분석: 어떤 edge가 더 잘 / 못 보존되었나 (§6 3가지 가설)
- [ ] 블로그 draft 0: "왜 측정이 필요했나 + Phase 0 이야기"

**Gate 2 체크:**

- [x] 실험 A 4차원 벡터 실제 수치 존재 — 위 snapshot §2
- [x] LangSmith run diff URL 확보 — snapshot §1.1
- [x] Edge preservation fail이 수치로 드러남 — pseudo_anim/anim_codegen 50% → 68.8%, render_qa 68.75% → 62.5%
- [x] **면접 Ready 라인 2 확보** — "단일 aggregate 지표는 CONDENSED를 '열등'으로 판정했지만, edge 단위 벡터는 +18.8%p/+18.8%p/0/−6.25%p tradeoff를 드러냈다. prompt-only 최적화는 천장에 닿았다"

**Gate 2 판정 (2026-04-13):** 통과.
- CONDENSED를 default로 스위칭 **안 함** (render_success −12.4%p, QA −1.14 이 user-facing 품질 훼손)
- 측정 인프라가 의사결정을 흔드는 신호를 생성했다는 사실 자체가 Phase 1의 목표
- `pseudo→anim` edge의 +18.8%p 개선 신호는 Week 4 IntentTracker 설계의 직접 근거

**DoW:** 실험 A diff 리포트 + snapshot md. **Gate 2 통과 → Phase 2 (Week 4) 착수.**

---

## Phase 2 — IntentTracker + 실험 B + Judge Calibration (Week 4-5)

> **Scope revision (2026-04-13).** 원래 플랜은 "Claude Agent SDK + gifpt_v2 스캐폴드"였으나, Week 3 Gate 2 결과와 사용자 피드백을 반영해 **IntentTracker-first on existing linear pipeline with gpt-4o**로 범위를 좁힘.
> **근거:** Agent SDK를 쓰면 v1(gpt-4o) vs v2(Claude) 비교 시 "아키텍처 변화"와 "모델 변화"가 동시에 움직여 IntentTracker 효과를 측정 불가능. Week 3 통제 원칙과 정면 충돌.
> **방침:** v2 모듈 스캐폴드 / Agent SDK / 5 tools 정의는 Phase 2 이후 별도 실험으로 연기. Week 4는 IntentTracker 단독 효과 측정에 집중.

### Week 4 — IntentTracker (observability → injection)

**관찰:** 기존 4 edge evaluator는 이미 pairwise intent tracker 역할을 한다 (pseudo→anim 엔티티 보존 체크 등). IntentTracker가 새로 주는 신호는 ① `user_text → pseudo_ir` 최초 edge의 loss 감지, ② canonical intent anchor로 전 파이프라인 transitive 체크, ③ lost intent를 다음 stage에 inject해서 복구하는 fix mode.

- [x] **D1** `studio/ai/intent_tracker.py` ✅
  - [x] `IntentSchema` pydantic model (`entities: list[str]`, `operations: list[str]`)
  - [x] `extract_intent(user_text) -> IntentSchema` — gpt-4o JSON mode
  - [x] `@traceable(name="intent_extract", run_type="chain")`
  - [x] 유닛 테스트 26개
- [x] **D2** `check_intent_loss(intent, artifact, stage)` deterministic matcher ✅
  - [x] `pipeline_capture.py`에 Stage 0 (extract) 삽입
  - [x] capture dict에 `intent`, `intent_loss: {pseudo_ir, anim_ir, codegen}` 기록
- [x] **D3** `studio/evaluators/intent_preservation.py` — 5번째 evaluator ✅
  - [x] `langsmith_adapter.py` 연결
  - [x] 유닛 테스트 10개 (non-dict stage_errors 가드 포함, Copilot 리뷰 반영)
- [x] **D4 실험 C (observability-only)**: goldset v0 × FULL × gpt-4o × IntentTracker ✅
  - [x] 5-dim 벡터 수집 (`v1_exp_c_intent_full-23362d9d`, 16/16, 12:28)
  - [x] 기존 4-dim 대비 intent_preservation이 새 신호를 주는지 확인 — **예, user→pseudo_ir에서 30% 손실 포착**
- [x] **D5 중간 판정**: `docs/snapshots/experiment-c-intent-observability.md` ✅
  - [x] user→pseudo edge에 실제 loss가 잡히는가? — **예, pseudo_ir mean rate 0.706**
  - [x] 어느 stage가 최악인가? — **pseudo_ir가 가장 큰 drop point (user text→30% 손실)**. anim_ir(0.615), codegen(0.631)은 추가 ~10%만 더 잃음.
  - [x] 다음 단계 결정: **Week 5 Experiment B (pseudo_ir prompt에 intent JSON 주입) 진행**. 목표: pseudo_ir rate 0.706 → ≥0.85, overall rate 0.655 → ≥0.80
- [ ] **D6–7 (선택)** injection mode: lost intent를 다음 stage system prompt에 힌트로 주입 → Week 5 D1–D3로 승격
  - [ ] 실험 B: injection OFF / pseudo_ir only / all 3 stages 3-arm 비교

**DoW:** 5-dim 벡터가 LangSmith에 수집되고, user→pseudo edge loss가 숫자로 드러나거나 "신호 없음"이 확정됨. → ✅ **달성** (2026-04-14). 30% 손실이 숫자로 드러남. Week 4 노이즈 envelope ≈ ±2 케이스 / ±3%p 확정. Week 5 Experiment B 진행 결정.

**Week 4 원칙 (Week 3에서 계승):** 모든 실험에서 3 LLM stage는 `gpt-4o` 통일. IntentTracker 호출도 `gpt-4o`. 변수는 "IntentTracker 유무" 하나만 움직인다.

### Week 5 — 실험 B (IntentTracker ON vs OFF) + Judge Calibration + Gate 3

> **Scope revision (2026-04-13).** 실험 B는 "v1 vs v2" 아키텍처 대결이 아니라, **동일 linear pipeline + gpt-4o** 위에서 IntentTracker injection mode ON vs OFF 비교로 재정의. 독립변수 하나만 움직이는 게 Week 3/4 통제 원칙과 일관됨.

- [ ] **실험 B run**: IntentTracker injection ON × goldset v0 (16 case, gpt-4o, FULL 프롬프트)
- [ ] LangSmith run diff: Week 3 FULL baseline (`b4315c13-7e06-4acf-a6fc-1e6ccfbe5722`) vs B
- [ ] 핵심 측정: edge preservation 4개 + intent_preservation 5번째, mean QA, render success
- [ ] 기대 지점: `anim_ir → codegen` edge의 `_UNKNOWN_HELPERS` 감소, `pseudo→anim` 보존률 개선
- [ ] 수치 박제: `docs/snapshots/experiment-b-intent-injection.md`

**Abort gate (Week 4 말 / 실험 C 이후 판정):**

| 지표 | Week 3 baseline (FULL) | 실험 B 목표 | Abort 조건 |
|---|---:|---:|---|
| Edge preservation 평균 | 0.578 (= (0.50+0.50+0.625+0.6875)/4) | **≥ 0.75** | < 0.70 시 abort |
| Mean QA score | 5.78 | **≥ 6.5** | < 6.0 시 abort |
| Render success | 81.2% | ≥ 81.2% (회귀 없음) | < 75% 시 abort |

**Abort 시 행동:** IntentTracker 접근을 접고, Week 3 tradeoff 데이터로 돌아가 "prompt-level 조작이 아니라 stage 간 정보 구조 자체를 바꿔야 한다"의 대안 가설(ex. 구조화 IR 포맷 강제, 혹은 codegen → render 사이 AST validator 강화)을 재검토. Sunk cost fallacy로 Week 5–7 끌지 않는다.

- [ ] **Judge self-calibration** ★
  - [ ] 사용자에게 **20 golden edge 수기 라벨링** 요청
  - [ ] Judge 실행 → 20 golden edge agreement 계산
  - [ ] Agreement ≥ 85% 확인 (**Gate 3**)
  - [ ] 미달 시 rubric 재튜닝 → 재측정
- [ ] `docs/judge-calibration-report.md` 작성

**Gate 3 체크:**

- [ ] 실험 B 5차원 벡터 존재 (abort gate 통과)
- [ ] Judge agreement ≥ 85%
- [ ] Edge preservation fail rate 변화 정량화
- [ ] **면접 Ready 라인 3 확보** — "측정 도구 자체의 신뢰도를 검증했고, IntentTracker로 edge 보존을 X→Y로 끌어올렸다"

**Gate 3 실패 시** → Week 6을 Week 5 후반으로 연장, rubric 재튜닝.

**DoW:** 실험 B 리포트 + calibration 리포트 + snapshot 2개.

---

## Phase 3 — Writeup + 면접 Prep (Week 6)

### Week 6 — 블로그 + 이력서 + Pitch

- [ ] 블로그 1편 완성 (3부작 아닌 1편 — pivot 반영)
  - [ ] 도입: `scripts/README.md:103-104` 인용문 앵커
  - [ ] 본론: 3 axiom (delta / edge-first / dynamic graph) + LangSmith 선택 근거
  - [ ] 실험 A/B 결과 + 실제 수치
  - [ ] Judge calibration 방법론
  - [ ] 교훈: "측정 가능성 자체를 설계 목표로"
- [ ] 이력서 업데이트
  - [ ] GIFPT 프로젝트 bullet 재작성: "edge-level 측정으로 X개 edge preservation 이슈 발견 → v2에서 Y% 개선"
  - [ ] LangSmith 경험 추가
- [ ] 면접 pitch
  - [ ] 30초 엘리베이터 (3 axiom)
  - [ ] 2분 상세 (실험 A + B + calibration)
  - [ ] Q&A 대비: `gifpt-measurement-driven-refactor.md §6` 표 암기
- [ ] GIFPT default route v1 → v2 스위칭 (Day 1 답변 D 기준 충족 시)

**Gate 4 체크:**

- [ ] 블로그 draft 1 완성
- [ ] 이력서 업데이트 완료
- [ ] 면접 pitch 최소 1회 자가 리허설

**DoW:** 3 산출물 모두 존재 + narrative 성립 self-check 통과.

---

## 버퍼 (Week 7-8)

- [ ] 발견된 버그 수정
- [ ] (선택) 실험 C — v2 codegen model 3-way A/B (gpt-4o / gpt-4.1 / claude-sonnet-4-6)
- [ ] 포스트모템 문서 작성
- [ ] 블로그 publish (Day 1 답변 E 기준)
- [ ] 면접 대비 Q&A 롤플레이

---

## 진행 상황 추적

**현재 Phase:** Week 2 Phase 1 (4 custom evaluator 구현 중)
**완료된 Gate:** Gate 0, Phase 0 산출물 3/3 self-review ✅ (user review 대기)
**다음 마일스톤:** 4 evaluator 구현 + 단위 테스트 → Gate 2 (Week 3 실험 A)

### 주간 자가 점검 질문

매주 금요일 이 3개 질문에 답한다:
1. 이번 주 DoW 통과했는가?
2. 다음 주 차단 요인은 무엇인가?
3. **지금 면접을 본다면 narrative가 성립하는가?** (Week 1 이후 항상 "예"여야 함)

3번 답이 "아니오"면 새 코드 작성 중단, narrative 산출물부터 복구.

---

## 긴급 중단 조건 (Abort Gate)

다음 중 하나라도 발생 시 즉시 사용자 보고 및 플랜 재검토:

- [ ] LangSmith billing 예상치 초과 (> $20 / week)
- [ ] Week 2까지 4 evaluator 중 2개 이상 구현 실패
- [ ] Week 5에 judge agreement < 70% (85% 미달의 2배 이상 차이)
- [ ] GIFPT 본체에 예상보다 큰 침습이 필요한 것이 발견됨 (`@traceable` 주입 이상)
- [ ] Claude Agent SDK major breaking change

---

## 참조

- **Canonical plan:** `gifpt-measurement-driven-refactor.md`
- **Pivot 결정 기록:** `../docs/build-vs-buy-spike.md`
- **아카이브 (이전 15주 플랜):** `archive/harness-ci-narrative.md`, `archive/harness-ci-plan-v2.md`

*이 문서는 실행 상태에 따라 **매주 업데이트**. 완료 항목에 `[x]` 표시 후 commit.*
