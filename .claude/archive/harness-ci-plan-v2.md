# Harness CI × GIFPT — 최적 실행 계획 (Synthesis v2)

> **작성일:** 2026-04-12
> **상태:** canonical. 이 문서가 실행 기준. 두 원본은 아카이브.
> **원본:**
> - `harness-ci-narrative.md` — narrative reframing + Phase 0 제안 + delta-over-quality axiom
> - 인수인계 문서 v1 — edge-first axiom + 스키마/VCR/v2 설계 + 13주 플랜
> **이 문서의 역할:** 두 원본의 강점을 병합하고, 세 개의 긴장점(2주 vs 13주, edge vs ladder, build-vs-buy 부재)을 해소한다.

---

## 0. TL;DR (30초)

1. **두 원본 모두 맞다.** Phase 0(내 문서)을 Phase 1(user 문서) 앞에 삽입하면 양립한다. 결과는 **15주(=2 + 13)** 플랜.
2. **Axiom 3개로 확장** — delta(WHY) + edge-first(HOW) + dynamic graph(WHAT). User 문서의 2 axiom에 "왜 edge를 측정하는가"의 메타 layer를 얹는다.
3. **Day 0 Build-vs-Buy 스파이크(30분)** 추가. promptfoo/Inspect에 edge 개념이 실제로 없음을 본인 손으로 확인한 증거가 있어야 "공백 포지션" narrative가 정당하다. 만약 있다면 15주를 2주로 압축한다 — 나쁜 뉴스 아님.
4. **Django + Celery를 Week 3 → Week 8로 미룬다.** Phase 1은 Pure Python CLI + SQLite + `multiprocessing`으로 충분. Celery는 GIFPT v2 agent loop이 실제로 병렬을 필요로 하는 Week 8에 도입.
5. **면접 Ready 라인 2개**: Week 2 말(Phase 0 완료, 문서만) / Week 7 말(Phase 1 완료, 실제 리포트). 어느 쪽이 슬립해도 다른 쪽이 보험이다.
6. **Go/No-Go 게이트 2개**: Day 0 스파이크 결과 + Phase 0 문서 사용자 승인. 둘 중 하나라도 "no"면 Phase 1 착수 중단.

---

## 1. 통합 Axiom (3개)

### Axiom 1 — Delta over quality (WHY)
> "영상 품질은 단일 숫자로 측정 불가능하다. 그래서 quality 측정을 포기하고 **run-to-run delta**를 측정한다. Regression detection은 quality estimation보다 훨씬 싼 문제다."

**함의:**
- 단일 "quality score"를 만들려는 시도는 거짓 정밀도. 하지 말 것.
- "v2가 더 좋은가"는 대답할 수 없는 질문. "v1 → v2 변화 벡터"는 대답할 수 있는 질문.
- 리포트는 단일 숫자 아닌 **다차원 벡터**로 출력: `{기존 실패 감소율, 새 실패 등장률, 토큰 델타, 도메인별 회귀 여부}`.

이것이 edge-first가 왜 필요한가의 대답이다. 측정 단위가 edge라는 건 **mechanism**이고, delta 측정이라는 건 **reason**이다.

### Axiom 2 — Edge-first measurement (HOW)
> "측정의 제1 단위는 stage가 아니라 **edge(handoff)**. Stage pass/fail은 부산물, edge integrity가 본질."

**근거:** GIFPT 실패의 실제 형태는 모두 edge 누수다.

| 실패 | Edge | 증거 |
|---|---|---|
| `_UNKNOWN_HELPERS` (AddPointToGraph 등) | codegen → render | AST validator 통과, Manim 런타임 크래시. `llm_codegen.py:427-433` |
| LSM-Tree → sorting 오분류 | domain classifier → anim IR | 빈 trace 전달, 다운스트림 도미노. `video_render.py:307-317` |
| `sorting.comparison_shown -2.5` 페널티 | anim IR → codegen | "비교" 개념이 조용히 증발. `qa.py:275-342` |
| `post_process_manim_code` 21 color + 9 helper regex | codegen → render | 수작업 덮기. `llm_codegen.py:436-506` |

**측정 primitives (edge 위에 올리는 assertion 4종):**
1. **Handoff schema** — Pydantic 검증 (구조)
2. **Preservation** — entity/operation count 보존 (의미)
3. **LLM judge** — 한국어 rubric으로 `(upstream, downstream)` 쌍 판정 (의도 보존)
4. **Downstream causation** — stage N+2 실패 시 어느 edge가 원인이었는지 역추적

**Stage 메트릭은 부수 지표로 강등.** pass rate, 토큰, 시간은 유지하되 edge integrity 아래 배치.

### Axiom 3 — Dynamic-ready data model (WHAT)
> "Trajectory는 dynamic directed graph. 노드 = agent step, edge = handoff. Fixed pipeline은 이 그래프의 degenerate case(노드 4개, 체인)."

**함의:**
- 저장 모델은 `trajectory(id) → nodes[] → edges[]` 형태 고정.
- Level 0(GIFPT v1 현재)도, Level 2(GIFPT v2)도, Level 3(Planner-Executor-Critic)도 **같은 스키마**로 돌아가야 한다.
- 처음부터 이 가정으로 가지 않으면 Phase 3에서 재설계 필요.

**절대 흔들지 말 것:** §4의 SQLite 스키마를 "간단하게" 줄이는 리팩터는 금지. Level 0/2/3 호환성이 깨지면 플랜 전체가 무너진다.

---

## 2. 통합된 Phase 플랜 (15주 + 버퍼)

```
Day 0  : Build-vs-Buy spike (30분) ─────────────── Go/No-Go #1
Week 1-2: Phase 0 — Narrative 산출물 ───────────── 면접 Ready 라인 1
         사용자 승인 ─────────────────────────── Go/No-Go #2
Week 3-7: Phase 1 — Harness CI MVP ──────────────── 면접 Ready 라인 2
Week 8-11: Phase 2 — GIFPT v2 + edge judge + Celery
Week 12-13: Phase 3 — 공개 + 두번째 어댑터
Week 14-15: 버퍼
```

### Phase -1 — Day 0 Build-vs-Buy 스파이크 (30분) ★NEW★

**목적:** "공백 포지션" narrative의 물증 확보. Harness CI를 직접 만드는 의사결정을 정당화하거나 기각한다.

**작업:**
1. **promptfoo 공식 문서** — 검색어 `multi-stage`, `pipeline`, `handoff`, `edge`, `agent trajectory`
2. **Inspect AI 공식 문서** (UK AISI) — 같은 검색
3. **LangSmith / Braintrust** — trace viewer 에서 edge-level diff 기능 유무
4. **Weave (W&B)** — agent evaluation 기능
5. 결과를 `docs/build-vs-buy-spike.md` 한 장으로 기록

**Go 조건 (자체 빌드 정당):** 위 4개 중 어느 것도 "run-to-run edge-level preservation diff" 기능 없음 확인. 면접 narrative에 이 스파이크 결과를 직접 인용 가능.

**No-Go 조건 (자체 빌드 부적절):** promptfoo/Inspect가 이미 edge 개념을 구현했거나, 200줄 어댑터로 80% 해결 가능. 이 경우 15주 플랜 **폐기**, 2주 어댑터 플랜으로 전환. **시간 13주 절약 = 나쁜 뉴스 아님.**

**이 스파이크 없이 Phase 1로 직행하지 말 것.** 나중에 면접관이 "왜 직접 만들었나"를 물을 때 대답이 없다.

### Phase 0 — Narrative 산출물 (Week 1-2) ★NEW from my doc★

**목적:** 면접 Ready 라인 1을 확보한다. Phase 1이 슬립해도 이 2주 산출물만으로 narrative 성립.

**중요:** 이 단계에서는 **Harness CI 리포 생성 금지**. GIFPT 리포에 바로 commit. 새 코드 0줄, 문서만.

**산출물:**

| 파일 | 내용 | 근거 소스 |
|---|---|---|
| `gifpt/docs/failure-taxonomy.md` | `failure_audit.py` 6-stage taxonomy + weekly_audit 실패 20개 수동 분류 + edge 원인 mapping | `scripts/failure_audit.py`, `scripts/weekly_audit.py` |
| `gifpt/docs/v1-baseline-report.md` | 16 seed × stage pass rate + failure class 분포 + edge preservation fail 수동 카운트 (숫자 한 장) | `seed_examples.jsonl`, `seed_audit.py` 재실행 |
| `gifpt/docs/edge-first-measurement.md` | §1의 3 axiom + edge 증거 4개(§1 Axiom 2 표) + delta vs quality 철학 + 경쟁 지형 | 본 문서 §1 + `scripts/README.md:103-104` 인용문 |

**Phase 0 DoD:**
- 3 문서 모두 사용자(우태호) 승인
- `scripts/README.md:103-104` 인용문이 `edge-first-measurement.md`에 앵커 역할로 배치됨
- "v1 baseline report"에 최소 4개 edge preservation 실패 케이스가 수치로 기록됨

**Week 2 말 면접 Ready 라인 1:**
> "v1을 정량 해부했고, edge-first 측정 philosophy를 확정했습니다. 회귀 테스트 인프라 구축이 다음 단계인데 현재 진행 중입니다."

이 라인은 이미 대부분의 면접관한테 enough. 시니어일수록 "완료된 프로젝트"보다 "현재 씨름 중인 문제"에 관심 있다.

### Phase 1 — Harness CI MVP (Week 3-7, Narrowed)

**변경점 (user 문서 대비):**
- Django REST 제거, **Pure Python CLI + SQLite only**
- Celery 제거, `multiprocessing.Pool`로 충분 (Phase 2에서 Celery 도입)
- 나머지(스키마, adapter, VCR, edge judge)는 user 문서 §5 그대로 유지

**Week 3 — Bootstrap + 스키마 + VCR**
- `harness-ci` 독립 리포 생성, `pyproject.toml`, pre-commit
- SQLite 스키마 v0 (§4) Alembic migration 작성
- OpenAI VCR (§5) 완성 + 단위 테스트 3개. **VCR을 Week 3 이후로 미루지 말 것.**
- GIFPT 본체에 최소 침습 PR: `openai.OpenAI()` → `gifpt.llm.get_client()` factory 분리

**Week 4 — Adapter + Goldset import**
- `harness_ci.adapters.base.Adapter` Protocol (§5-4)
- `adapters/gifpt/__init__.py` — 1 케이스 통과
- `seed_examples.jsonl` → goldset v0 import
- Phase 0에서 수동 분류한 weekly_audit 실패 20개를 goldset v0.5로 승격

**Week 5 — Stage pass rate + Edge schema assertion**
- `harness-ci run --adapter gifpt --goldset v0` CLI 동작
- Stage pass rate 계산
- Edge schema + preservation assertion 1차
- 기본 HTML 리포트 (stage bar chart만)

**Week 6 — Edge preservation + LLM judge 스켈레톤 + HTML diff**
- Edge preservation(entity/operation count) fail 검출
- LLM judge는 스켈레톤만 (rubric 미완성 OK)
- `harness-ci diff run_A run_B` HTML diff 리포트
- 한국어 judge rubric 초안 (Week 7에 사용자 review)

**Week 7 — Baseline + 첫 실제 실험 (실험 A)**
- Baseline run: `PEDAGOGICAL_RULES_FULL` × 16 seed
- 첫 실험: `PEDAGOGICAL_RULES_CONDENSED` × 16 seed
- Diff 리포트로 "3 cases turned green, 1 case turned red, cost -18%" 형태 수치 확보
- 블로그 draft 0

**Week 7 말 면접 Ready 라인 2:**
> "v1 회귀 테스트 인프라 완성. 첫 prompt 실험에서 'CONDENSED는 토큰 -X%, Y 도메인에서 회귀 +Z%' 벡터 확인. 다음은 agentic loop 리팩터."

### Phase 2 — GIFPT v2 + Edge LLM-judge + Celery (Week 8-11)

**변경점:** Celery를 이 Phase에서 도입. 이유: v2 agent loop(max 25 turn) × 16 case = 400+ LLM 호출 가능성. Serial 실행 시 1 run 1시간+ 예상. 병렬 ON이 실질 효용 있음. 반면 Phase 1 v1은 64 LLM 호출이라 serial로 견딜만함.

**Week 8 — v2 스켈레톤 + Celery 도입**
- Claude Agent SDK + 5 tools + IntentTracker 골격 (user 문서 §6 그대로)
- 1 케이스 end-to-end 통과
- Celery + Redis worker 세팅 (GIFPT 스택 재사용 서사 정합)

**Week 9 — v2 full + Edge LLM-judge rubric 완성**
- v2 completion on 16 seed
- Edge judge 한국어 rubric (Week 6에 초안, 이제 golden sample과 함께 calibrate)
- **Judge self-calibration 추가** (★ 내 문서 기여): 20개 수동 라벨링 golden edge + judge agreement ≥ 85% 확인. Agreement 낮으면 rubric 재튜닝.
- v1 vs v2 trajectory diff HTML

**Week 10 — 실험 B (v1 vs v2) + 실험 C (Model routing A/B)**
- 실험 B: IntentTracker 효과 검증. 예상 결과 "v1의 anim_ir → codegen edge 실패 5건 중 4건이 v2에서 intent_check turn에 의해 교정"
- 실험 C: codegen model 3-way A/B (gpt-4o / gpt-4.1 / claude-sonnet-4-6)

**Week 11 — Attribution graph + 리포트 정리 + 블로그 draft 1**
- Downstream 실패 → 원인 edge 역추적 UI
- Phase 2 정리 리포트

### Phase 3 — 공개 + 일반화 (Week 12-13)

user 문서 §8 Phase 3 유지. README + DEMO 영상 + Velog 3부작 + 두번째 adapter (남사칭 rerank) + GitHub Action template.

**단, 공개 시점을 고정 목표로 두지 말 것.** 공개 압박이 도구 자체 가치 판단을 왜곡한다. Phase 2 결과를 보고 공개 여부 최종 결정.

### 버퍼 (Week 14-15)

예비 / 이력서 업데이트 / 면접 준비 / bug fix.

---

## 3. 업데이트된 ADR 재검토

| 결정 | user 문서 | synthesis 수정 | 이유 |
|---|---|---|---|
| Python 3.12 | ✓ | ✓ 유지 | |
| **Django REST** | Week 1부터 | **Week 8부터** (Phase 2) | Phase 1은 CLI + SQLite만 필요. Django admin/HTTP는 v2 대시보드가 실제로 필요해질 때 도입. Week 1~7에 얹으면 migrations/settings 부수 복잡도가 Phase 1 속도를 먹는다. |
| SQLite + Alembic | ✓ | ✓ 유지 | |
| **Celery + Redis** | Week 7부터 | **Week 8부터** (Phase 2) | v2 agent loop에서 400+ LLM 호출 필요해지는 시점에 도입. Phase 1(v1 64 호출)은 `multiprocessing.Pool`로 충분. |
| **OpenAI VCR** | Week 1 | **Week 3** (Phase 1 Week 1) | Phase 0은 새 코드 없음. VCR은 Phase 1 착수와 동시. 우선순위 최상위 유지. |
| in-process 샌드박스 | ✓ | ✓ 유지 | |
| Dogfood GIFPT only | Week 1-6 | Week 3-10 | Phase 번호 shift 반영 |
| GitHub Action | Phase 3 | ✓ Week 12 | |
| **Build-vs-buy 스파이크** | 없음 | **Day 0 필수** ★NEW★ | narrative 정당성 검증. 결과에 따라 플랜 통째로 변경 가능. |
| **Phase 0 narrative 산출물** | 없음 | **Week 1-2 필수** ★NEW★ | 면접 Ready 라인 보험. Phase 1 슬립 대비. |
| **LLM judge self-calibration** | 없음 (judge만 언급) | **Week 9에 20 golden edge** ★NEW★ | Judge drift 대응. "자신의 메트릭을 불신할 줄 안다"는 narrative 증거. |

---

## 4. SQLite 스키마 v0 (user 문서 §5-3 그대로 보존)

> **절대 단순화 금지.** Level 0/2/3 호환성 유지.

```sql
CREATE TABLE run (
    id          INTEGER PRIMARY KEY,
    created_at  TIMESTAMP NOT NULL,
    adapter     TEXT NOT NULL,
    goldset_id  TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    git_sha     TEXT,
    label       TEXT,
    notes       TEXT
);

CREATE TABLE case_run (
    id          INTEGER PRIMARY KEY,
    run_id      INTEGER REFERENCES run(id),
    case_id     TEXT NOT NULL,
    status      TEXT NOT NULL,
    total_cost_usd   REAL,
    total_latency_ms INTEGER,
    failure_edge_id  INTEGER
);

CREATE TABLE node (
    id            INTEGER PRIMARY KEY,
    case_run_id   INTEGER REFERENCES case_run(id),
    step_index    INTEGER NOT NULL,
    agent_name    TEXT NOT NULL,
    action        TEXT NOT NULL,
    input_hash    TEXT,
    output_hash   TEXT,
    input_blob    TEXT,
    output_blob   TEXT,
    model         TEXT,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    cost_usd      REAL,
    latency_ms    INTEGER,
    status        TEXT
);

CREATE TABLE edge (
    id              INTEGER PRIMARY KEY,
    case_run_id     INTEGER REFERENCES case_run(id),
    from_node_id    INTEGER REFERENCES node(id),
    to_node_id      INTEGER REFERENCES node(id),
    edge_kind       TEXT NOT NULL,
    schema_pass     BOOLEAN,
    preservation_pass BOOLEAN,
    judge_pass      BOOLEAN,
    judge_score     REAL,
    judge_reason    TEXT,
    causation_target_node_id INTEGER
);

CREATE TABLE openai_cache (
    key         TEXT PRIMARY KEY,
    response    TEXT NOT NULL,
    created_at  TIMESTAMP NOT NULL,
    hit_count   INTEGER DEFAULT 0
);
```

---

## 5. OpenAI VCR + Judge Calibration

### 5-1. VCR (user 문서 §5-5 그대로)

`hash(model, temperature, messages, tools, seed)` 기반 record/replay. GIFPT 본체에 client factory 하나만 분리하고 Harness CI가 factory에 `VCRClient` 주입. Replay mode에서 cache miss = **fail loudly** (조용히 실제 호출 금지, CI 비용 폭발 방지).

### 5-2. Judge self-calibration ★NEW★

LLM judge는 또 다른 측정 대상이다. 해결:

1. Week 6 rubric 초안 → Week 7 사용자 review
2. Week 9에 사용자가 20개 golden edge 수동 라벨링 (✓ 정보 보존 / ✗ 누수)
3. Judge 실행 → agreement 계산 → ≥ 85% 확인
4. Agreement 낮으면 rubric 재튜닝 + 재측정
5. 결과를 `judge-calibration-report.md`에 기록

**면접 asset:** "자동 메트릭을 만든 사람은 많지만, 자기 메트릭을 불신할 줄 아는 사람은 드물다. Agreement 85% 미만이면 judge 숫자 자체를 신뢰하지 않도록 설계했다."

---

## 6. Adapter Protocol (user 문서 §5-4 그대로)

```python
class Adapter(Protocol):
    name: str
    def load_goldset(self, goldset_id: str) -> Iterable[GoldCase]: ...
    def run_case(self, case: GoldCase, config_overrides: dict) -> TrajectoryResult: ...
    def build_edges(self, steps: list[StepRecord]) -> list[dict]: ...
    def assert_edge(self, edge: dict, upstream: dict, downstream: dict) -> dict: ...
```

세부 타입 정의는 user 문서 §5-4 참조.

---

## 7. GIFPT v2 (Level 2) 아키텍처

user 문서 §6 **완전 보존**. Claude Agent SDK + 5 tools + IntentTracker. v1 자산 매핑 표도 그대로 유지.

**단, 착수 시점은 Week 6 → Week 8로 shift** (Phase 0 2주 삽입으로 인한 번호 이동).

---

## 8. 면접 narrative (통합 버전)

### 30초 pitch

> "제 GIFPT 프로젝트 — Next.js / Spring Boot / Django·Celery·Redis 3-tier 알고리즘 애니메이션 생성기 — 가 4-stage LLM 파이프라인의 프롬프트 엔지니어링 한계에 도달했을 때, 저는 두 가지를 알아챘습니다.
>
> 첫째, **영상 품질은 단일 숫자로 측정 불가능합니다.** 그래서 저는 품질 측정을 포기하고 **run-to-run delta**를 측정하는 쪽으로 문제를 재정의했습니다.
>
> 둘째, 측정의 최소 단위는 stage가 아니라 **edge(단계 간 handoff)** 입니다. 실제로 GIFPT 실패의 대부분 — `_UNKNOWN_HELPERS`, LSM-Tree 오분류, 21개 color regex 수작업 덮기 — 가 모두 handoff 누수였습니다.
>
> 그래서 edge-first 회귀 테스트 도구 Harness CI를 만들었습니다. 첫 dogfood는 GIFPT 자체를 agentic loop(Level 2)로 리팩터한 GIFPT v2이고, 두 버전을 edge 단위로 diff한 결과를 블로그로 공개했습니다.
>
> 소유자(본인)가 `scripts/README.md`에 직접 'CI regression tests are a separate piece of work that will eventually consume the same seed_audit.py machinery'라고 써둔 그 문장을 구현한 겁니다."

### 한 줄 버전

> "저는 측정할 수 없는 것을 측정하려고 시간을 쓰지 않습니다. 대신 측정할 수 있는 것 — edge의 delta — 만으로 의사결정이 가능하도록 문제를 재정의합니다."

### 보조 질문 대응

- **"왜 promptfoo/Inspect 말고 직접 만들었나?"** → Day 0 스파이크 결과 인용. "edge-level preservation diff 기능이 세 도구 모두에 없습니다."
- **"quality를 측정 안 하면 어떻게 좋아졌는지 아나?"** → "단일 숫자는 거짓말입니다. 4차원 벡터로 보고합니다: 기존 실패 감소, 새 실패 등장, 토큰 델타, 도메인별 회귀. 이 벡터가 실제 의사결정을 가능하게 합니다."
- **"LLM judge도 틀릴 수 있지 않나?"** → "맞습니다. 그래서 20개 golden edge로 agreement ≥ 85%를 calibrate하고, 그 이하면 judge 숫자를 신뢰하지 않습니다. 자기 메트릭을 불신할 줄 아는 게 측정 규율의 핵심입니다."

---

## 9. 열린 결정사항 (9개)

user 문서 §11의 6개 + synthesis 추가 3개.

**[원본 6개 — Day 1에 사용자 질의]**
1. **A. GIFPT v2 refactor level** — Level 2(single agentic loop) 확정? Level 3(Planner-Executor-Critic) 원하는가?
2. **B. Implementation framework** — Claude Agent SDK vs 자체 구현? (권장: SDK)
3. **C. Repo 구성** — `harness-ci` 독립 리포 vs GIFPT monorepo? (권장: 독립)
4. **D. Goldset 확장 시점** — Week 1(Phase 0) vs Week 7? (synthesis 권장: Phase 0에서 weekly_audit 실패 20개 수동 분류 → Week 4에 goldset v0.5로 승격)
5. **E. Timeline α vs β** — α: Harness CI 먼저(Phase 1) → GIFPT v2 나중(Phase 2). β: 병행. (권장: α)
6. **F. Korean LLM-judge rubric 골드셋** — 사용자가 수기 10-20개 예시 제공 가능? 언제? (권장: Week 6 초반 초안, Week 9 calibration)

**[★ Synthesis 추가 3개]**
7. **G. Build-vs-buy 스파이크 결과** — Day 0 스파이크에서 기존 도구 부재 확인되었는가? 만약 promptfoo/Inspect에 edge 개념이 이미 있다면 15주 플랜 **즉시 폐기**하고 2주 어댑터 플랜으로 전환.
8. **H. Phase 0 산출물 확인 게이트** — Week 2 말 3 문서(taxonomy/baseline/edge-philosophy) 사용자 review 완료를 Phase 1 착수의 필수 조건으로 둘 것인가? (권장: 예. Phase 0 승인 없이 Phase 1 착수 금지.)
9. **I. Django + Celery 도입 시점** — Week 3(user 원안) vs Week 8(synthesis 권장)? Week 8이 권장이지만 사용자가 "처음부터 풀스택 narrative"를 선호하면 Week 3 유지 가능 (대신 Phase 1 속도 손해 감수).

---

## 10. 리스크 등록 및 완화

| 리스크 | 가능성 | 완화 |
|---|---|---|
| 15주 플랜 슬립 (3주+ 지연) | **높음** | **Phase 0 면접 Ready 라인 1이 보험.** Week 2 말에 narrative 문서 3개 이미 확보. |
| GIFPT v2 + Harness CI 동시 작업으로 scope 붕괴 | 중 | Phase 1 → Phase 2 **완전 sequential**. 병행 금지. Week 7까지 v2 착수 금지. |
| OpenAI VCR miss 시 조용히 실제 호출 → 비용 폭발 | 중 | `replay_only` 기본값 + miss 시 fail loudly + 비용 알림 |
| 16 케이스 골드셋이 회귀 감지에 부족 (통계적 의미 없음) | **높음** | Phase 0에서 weekly_audit 실패 20개 수동 분류 → Week 4에 goldset v0.5로 승격 (16 → 36) |
| "Build-vs-buy 스파이크"에서 기존 도구 충분 판정 | 낮음-중 | **플랜 즉시 폐기**. 2주 어댑터 플랜으로 전환. 13주 절약. 나쁜 뉴스 아님. |
| Claude Agent SDK API 변경 | 낮음 | v2 구현 시 SDK 버전 핀 고정 |
| Django 도입 지연이 Phase 3 공개 시 "프로덕션 스택 아니다" 비판 | 낮음 | Week 12 공개 시 Django 이미 Phase 2에 도입되어 있음. 문제없음. |
| 한국어 judge rubric calibration 실패 (agreement < 85%) | 중 | Week 9에 드러남. Week 10 실험 B를 1주 지연하고 rubric 재튜닝. 버퍼 2주로 흡수 가능. |

---

## 11. 다음 에이전트 실행 지침

### 읽는 순서
1. §0 TL;DR — 30초
2. §1 Axioms — 모든 설계 판단의 기반. 외울 것.
3. §9 열린 결정사항 — **Day 1에 사용자 9개 질의**. 답 받은 뒤 본 문서 §9를 업데이트.
4. §2 Phase 플랜 — 매일 참조
5. §4 스키마, §5 VCR, §6 Adapter — 코드 쓸 때 참조

### Day 0 (필수, 30분)
1. Build-vs-buy 스파이크 실행
2. 결과를 `/Users/ehho/Desktop/GitHub/gifpt/docs/build-vs-buy-spike.md`에 기록
3. Go/No-Go 결정 사용자에게 보고

### Day 1
1. 사용자에게 §9 9개 결정사항 질의
2. 답 받은 뒤 §9 업데이트
3. **Go 판정이면 Phase 0 착수.** No-Go면 2주 어댑터 플랜으로 전환(별도 논의).

### Phase 0 (Week 1-2)
- `gifpt/docs/failure-taxonomy.md`
- `gifpt/docs/v1-baseline-report.md`
- `gifpt/docs/edge-first-measurement.md`
- **이 단계에서 Harness CI 리포 생성 금지.** 새 코드 0줄.
- Week 2 말 사용자 review → 승인 후 Phase 1 착수

### Phase 1 착수 전 필수 체크 (Go/No-Go #2)
- [ ] Day 0 스파이크 Go 판정
- [ ] Phase 0 3 문서 사용자 승인
- [ ] §9 9개 결정사항 답변 완료

**세 조건 모두 만족 시에만 Week 3 bootstrap 착수.**

### 절대 하지 말 것
- Phase 0를 건너뛰고 Phase 1 직행 (면접 보험 손실)
- Django + Celery를 Phase 1(Week 3-7)에 넣기 (Phase 1 완료 지연)
- GIFPT v2와 Harness CI를 동시 작업 (scope 붕괴)
- §4 SQLite 스키마를 "간단하게" 단순화 (Level 0/2/3 호환성 파괴)
- OpenAI VCR을 Week 3 이후로 미루기 (비용 폭발)
- "promptfoo 흉내" 언어 사용 (포지셔닝 오염)
- §1 3 axiom 흔들기 (프로젝트 정체성 손실)

### 반드시 할 것
- 매 PR마다 Harness CI 자기 자신의 goldset에도 통과하는지 확인 (self-dogfood)
- 모든 LLM 호출은 VCR 경유
- 한국어 judge rubric은 사용자 review 필수 (Week 6 초안, Week 9 calibration)
- 면접용 "before/after" 스냅샷을 실험할 때마다 `docs/snapshots/`에 박제
- 원본 문서 2개(`harness-ci-narrative.md`, 인수인계 문서 v1)는 **아카이브로 유지**. 이 문서(synthesis v2)만 canonical plan.

---

## 12. 원본 두 문서와의 관계

| 원본 | 역할 | 기여 | 상태 |
|---|---|---|---|
| `harness-ci-narrative.md` | narrative 초안 | Phase 0, delta-over-quality axiom, build-vs-buy 질문, 2주 Ready 라인, judge calibration | **아카이브** |
| 인수인계 문서 v1 | 풀빌드 설계 | Edge-first axiom, dynamic graph 스키마, VCR 설계, GIFPT v2 아키텍처, 경쟁 지형, 30초 pitch, GIFPT 파일 인덱스, 3 실험 설계 | **아카이브** |
| **본 문서 (synthesis v2)** | **canonical plan** | 두 원본의 통합 + 3 axiom 재구성 + 15주 플랜 + Go/No-Go 게이트 2개 + 9 열린 결정사항 | **active** |

두 원본은 삭제하지 말 것. 맥락 복원용으로 유지.

---

## 13. GIFPT 리포 참고 경로 (user 문서 §13 그대로)

| 파일 | 라인 | 내용 |
|---|---|---|
| `studio/tasks.py` | — | Celery entry `animate_algorithm` |
| `studio/video_render.py` | 68-84 | AST FORBIDDEN list |
| `studio/video_render.py` | 307-317 | LSM-Tree 오분류 docstring |
| `studio/ai/llm_codegen.py` | 29-30 | `MODEL_PRIMARY` / `MODEL_FAST` |
| `studio/ai/llm_codegen.py` | 34-99 | `PEDAGOGICAL_RULES_FULL/CONDENSED` |
| `studio/ai/llm_codegen.py` | 409-425 | 21 forbidden color regex |
| `studio/ai/llm_codegen.py` | 427-433 | `_UNKNOWN_HELPERS` |
| `studio/ai/llm_codegen.py` | 436-506 | `post_process_manim_code` |
| `studio/ai/llm_codegen.py` | 587-649 | QA feedback loop |
| `studio/ai/llm_codegen.py` | 699-755 | self-heal loop |
| `studio/ai/qa.py` | 275-342 | 도메인 페널티 |
| `studio/ai/examples/seed_examples.jsonl` | — | 16 seeds |
| `scripts/failure_audit.py` | — | 6-stage taxonomy |
| `scripts/seed_audit.py` | — | 16 seed QA |
| `scripts/weekly_audit.py` | — | 주간 fail rate |
| **`scripts/README.md`** | **103-104** | **"CI regression tests are a separate piece of work..." 인용문** |

---

## 14. 용어집 (확장)

| 용어 | 의미 |
|---|---|
| **Delta over quality** | 절대 품질 측정을 포기하고 run-to-run 변화량을 측정한다는 원칙 (Axiom 1) |
| **Edge / handoff** | agent N의 출력이 agent N+1의 입력으로 넘어가는 순간. 측정의 제1 단위 (Axiom 2) |
| **Edge integrity** | 한 edge에 대한 4종 assertion(schema, preservation, judge, causation) 통과 여부 |
| **Dynamic directed graph** | trajectory 저장 모델. 노드=step, 에지=handoff. Level 0/2/3 공통 (Axiom 3) |
| **Harness engineering** | 프롬프트 바깥의 모든 것 (agent loop, tool mgmt, state, error recovery) |
| **Trajectory** | 한 케이스의 실행 기록. 노드 + 에지의 directed graph |
| **Goldset** | 고정 입력 집합. v0 = seed_examples.jsonl 16개. v0.5 = +weekly_audit 실패 20개 |
| **OpenAI VCR** | `hash(model, temp, messages, tools, seed)` 기반 record/replay 캐시 |
| **Judge self-calibration** | LLM judge 출력을 20 golden edge와 agreement 측정. ≥85% 미달 시 rubric 재튜닝 (★ synthesis 추가) |
| **IntentTracker** | GIFPT v2에서 핵심 개념 보존을 매 turn 체크하는 컴포넌트 |
| **Attribution graph** | 다운스트림 실패 → 원인 edge 역추적 causal 그래프 |
| **Level 2** | single agentic loop + tools + IntentTracker (GIFPT v2) |
| **Phase 0 narrative 산출물** | Week 1-2에 GIFPT 리포에만 작성하는 3 문서. 면접 Ready 라인 1 보험 (★ synthesis 추가) |
| **Go/No-Go 게이트** | Day 0 스파이크 결과 + Phase 0 사용자 승인. 두 조건 통과해야 Phase 1 착수 (★ synthesis 추가) |
| **면접 Ready 라인** | 특정 시점까지 narrative가 성립하는 지점. 라인 1 = Week 2 말, 라인 2 = Week 7 말 |

---

*문서 끝. 다음 에이전트는 Day 0 Build-vs-Buy 스파이크부터.*
