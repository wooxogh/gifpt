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
- [ ] LangSmith live baseline run — Week 3 실험 A에서 실행 (비용 이유로 Week 2에서는 인프라만)
- [ ] Edge fail 카운트가 baseline 리포트 숫자와 일치 확인 — Week 3

**DoW:** 4 evaluator 모듈 + 단위 테스트 + LangSmith wiring + CLI 전부 존재, offline smoke PASS.
**실제 16 case × 4 evaluator 매트릭스는 Week 3 Phase 1 실험 A에서 수집.**

### Week 3 — 실험 A (Prompt 감량) + Gate 2

- [ ] **Baseline run**: `PEDAGOGICAL_RULES_FULL` × goldset v0 (16 case)
  - [ ] 4차원 벡터 기록: pass rate / cost / latency / judge score
- [ ] **실험 A run**: `PEDAGOGICAL_RULES_CONDENSED` × goldset v0 (16 case)
  - [ ] 같은 4차원 벡터 기록
- [ ] LangSmith run diff UI로 "X green, Y red, cost -Z%" 확인
- [ ] 수치 박제: `gifpt/docs/snapshots/experiment-a-prompt-tweak.md`
  - [ ] 원인 분석: 어떤 edge가 더 잘 / 못 보존되었나
- [ ] 블로그 draft 0: "왜 측정이 필요했나 + Phase 0 이야기"

**Gate 2 체크:**

- [ ] 실험 A 4차원 벡터 실제 수치 존재
- [ ] LangSmith run diff URL 확보
- [ ] Edge preservation fail이 수치로 드러남
- [ ] **면접 Ready 라인 2 확보** — "실험으로 돌려봤더니 이런 트레이드오프가 드러났다" 말할 수 있음

**DoW:** 실험 A diff 리포트 + snapshot md + 블로그 draft 0. **Gate 2 통과 시 Phase 2 착수.**

---

## Phase 2 — GIFPT v2 Level 2 + 실험 B + Judge Calibration (Week 4-5)

### Week 4 — GIFPT v2 스캐폴드 + IntentTracker

- [ ] `gifpt_v2` 모듈 생성
- [ ] Claude Agent SDK 통합 (Day 1 답변 A 기준)
- [ ] 5 tools 정의: `write_pseudo_ir`, `write_anim_ir`, `write_manim_code`, `render_video`, `score_with_vision_qa`
- [ ] 각 tool의 validator 이식 (v1 `qa.py`, `video_render.py` FORBIDDEN AST, `post_process_manim_code`)
- [ ] `IntentTracker` 구현 (`gifpt_v2/intent_tracker.py`)
  - [ ] `extract()` — user request에서 intent 추출 (entity + operation list)
  - [ ] `check()` — artifact에서 lost intent 감지
  - [ ] IntentTracker 자체에도 `@traceable` 주입
- [ ] Agent system prompt 간소화 (PEDAGOGICAL_RULES 유지)
- [ ] v2 1 케이스 end-to-end 통과
- [ ] v2 파이프라인에 4 evaluator 연결

**DoW:** v2 1 케이스가 LangSmith UI에 v1과 구분되는 trace로 나타남.

### Week 5 — 실험 B (v1 vs v2) + Judge Calibration + Gate 3

- [ ] **실험 B run**: v2 × goldset v0 (16 case)
- [ ] LangSmith에서 v1 baseline vs v2 diff 확보
- [ ] 핵심 측정: edge preservation fail rate 감소 (IntentTracker 효과)
- [ ] 기대 지점: `anim_ir → codegen` edge의 `_UNKNOWN_HELPERS` 감소
- [ ] 수치 박제: `gifpt/docs/snapshots/experiment-b-v1-vs-v2.md`

- [ ] **Judge self-calibration** ★
  - [ ] 사용자에게 **20 golden edge 수기 라벨링** 요청 (Day 1 답변 C 시점)
  - [ ] Judge 실행 → 20 golden edge agreement 계산
  - [ ] Agreement ≥ 85% 확인 (**Gate 3**)
  - [ ] 미달 시 rubric 재튜닝 → 재측정
- [ ] `gifpt/docs/judge-calibration-report.md` 작성

**Gate 3 체크:**

- [ ] 실험 B 4차원 벡터 존재
- [ ] Judge agreement ≥ 85%
- [ ] Edge preservation fail rate 변화 정량화
- [ ] **면접 Ready 라인 3 확보** — "측정 도구 자체의 신뢰도를 검증했다"

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
