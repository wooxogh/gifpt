# GIFPT Measurement-Driven Refactor — Canonical Plan

> **작성일:** 2026-04-12 (pivot 후)
> **상태:** canonical. 이 문서가 프로젝트 기준.
> **전신:** `archive/harness-ci-plan-v2.md` (15주 도구 빌드 플랜, 스파이크 결과로 superseded)
> **실행 체크리스트:** `plan.md`
> **의사결정 기록:** `../docs/build-vs-buy-spike.md`

---

## 0. TL;DR (30초)

1. **프로젝트 정체:** LLM eval 도구를 만드는 게 아니라, **LangSmith 위에서 edge-first 측정 레이어를 쌓아 GIFPT v1을 해부하고 v2(agentic loop)로 리팩터한다.** 결과는 면접 narrative + GIFPT 자체의 개선.
2. **Tech stack:** LangSmith (trace + run diff + golden set regression) + custom code evaluators 4개 (edge preservation) + Claude Agent SDK (GIFPT v2) + 기존 GIFPT 스택 유지.
3. **기간:** **6주** (4 Phase). 버퍼 2주. 총 8주.
4. **3 Axiom 유지:** Delta over quality (WHY) + Edge-first measurement (HOW) + Dynamic-ready data model (WHAT). 이 셋이 프로젝트 정체성. 흔들지 말 것.
5. **면접 narrative 핵심 한 줄:** *"저는 tool 만드는 사람이 아니라, 제 시스템을 측정 기반으로 개선하는 사람입니다. LangSmith 위에 edge preservation 레이어를 얹어 GIFPT v1을 해부하고 v2로 리팩터했습니다."*

---

## 1. 프로젝트 정체 (무엇이고 무엇이 아닌가)

### 이 프로젝트는…

- ✅ **GIFPT v1 → v2 리팩터 프로젝트**이며, 리팩터 의사결정을 **측정 기반**으로 내린다.
- ✅ **Edge-first measurement philosophy의 실증**이며, 실증의 수단은 LangSmith + custom evaluators.
- ✅ **본인 포트폴리오 + 면접 asset**. 학부생이 "측정 없이 리팩터 안 한다"는 시니어 규율을 증명하는 작품.
- ✅ **Dogfood**. LangSmith를 수동적으로 쓰는 게 아니라, edge preservation layer를 본인이 설계해서 얹는다.

### 이 프로젝트는 아니다…

- ❌ LLM eval 도구 제품
- ❌ 오픈소스 프레임워크
- ❌ 독립 리포 (Harness CI 같은 별도 프로덕트)
- ❌ 두 번째 어댑터로 일반화 증명
- ❌ Publicly launched tool with HN submission

---

## 2. 3 Axiom (프로젝트 정체성)

### Axiom 1 — Delta over quality (WHY)
> "영상 품질은 단일 숫자로 측정 불가능. 그래서 quality를 포기하고 **run-to-run delta**를 측정한다. Regression detection은 quality estimation보다 훨씬 싼 문제다."

**함의:**
- 단일 quality score는 거짓 정밀도. 하지 말 것.
- "v2가 더 좋은가"는 대답 불가. "v1 → v2 변화 벡터"는 대답 가능.
- 리포트는 **다차원 벡터** 형태: `{기존 실패 감소율, 새 실패 등장률, 토큰 델타, 도메인별 회귀}`.

### Axiom 2 — Edge-first measurement (HOW)
> "측정의 제1 단위는 stage가 아니라 **edge(handoff)**. Stage pass/fail은 부산물, edge integrity가 본질."

**GIFPT 실패 증거 (4개 edge 누수):**

| 실패 | Edge | 증거 |
|---|---|---|
| `_UNKNOWN_HELPERS` (AddPointToGraph 등) | codegen → render | AST validator 통과, Manim 런타임 크래시. `llm_codegen.py:427-433` |
| LSM-Tree → sorting 오분류 | domain classifier → anim IR | 빈 trace 전달, 다운스트림 도미노. `video_render.py:307-317` |
| `sorting.comparison_shown -2.5` 페널티 | anim IR → codegen | "비교" 개념이 조용히 증발. `qa.py:275-342` |
| `post_process_manim_code` 21 color + 9 helper regex | codegen → render | 수작업 덮기. `llm_codegen.py:436-506` |

**측정 primitives (각 edge에 올리는 assertion 4종):**
1. **Schema** — Pydantic 검증 (구조)
2. **Preservation** — entity/operation count 보존 (의미)
3. **LLM judge** — 한국어 rubric으로 `(upstream, downstream)` 쌍 판정 (의도)
4. **Attribution** — downstream 실패 → 원인 edge 역추적

### Axiom 3 — Dynamic-ready data model (WHAT)
> "Trajectory는 dynamic directed graph. 노드 = agent step, edge = handoff. Fixed pipeline은 degenerate case."

**함의:**
- v1(fixed 4-stage)도 v2(agent loop)도 **같은 개념**으로 측정 가능해야 함.
- LangSmith의 trace는 이미 tree 구조를 담을 수 있음 → Axiom 3은 **LangSmith 위에 edge-first view를 얹는 것**으로 실현.
- v1 4 edges (3 stage handoff + 1 render→qa), v2는 turn 수만큼 edges. 같은 evaluator 코드가 두 trajectory 모두에 작동.

---

## 3. Tech Stack 결정

### 3-1. 측정 인프라: LangSmith (★ 새 결정)

**선택 이유:**
- Run-over-run diff, side-by-side comparison 이미 제공
- Golden set regression 내장
- CI/CD 통합 (GitHub Action) 제공
- Per-step trace + custom code evaluator hook 제공
- Self-host 가능 (필요 시)
- **구현 시간 2주 절약** + **narrative 오히려 강화** (pragmatism 증명)

**사용 범위:**
- Trace 수집: GIFPT의 모든 LLM 호출을 LangSmith로 전송
- Dataset: goldset v0 (16 seeds) + v0.5 (+ weekly audit 실패 20개) 업로드
- Evaluation: custom code evaluator 4개로 edge preservation 체크
- Run diff: `langsmith` SDK로 두 run 비교, 간단 Jinja2 HTML 리포트 자체 생성 (LangSmith UI는 보조)

**하지 않는 것:**
- LangChain 프레임워크 의존 (GIFPT는 LangChain 안 씀, 그냥 OpenAI SDK + LangSmith tracing만 사용)
- LangSmith 고급 기능 (prompt hub, playground 등)

### 3-2. GIFPT v2: Claude Agent SDK + Level 2

**선택 이유:**
- GIFPT v1의 self-heal loop + QA feedback loop + post-process hacks 전부가 "프롬프트로 못 막는 handoff 누수"의 증거 → agent에게 재시도/tool 사용을 위임하는 Level 2가 자연스러운 해법
- Claude Agent SDK가 tool use + turn loop을 가장 깔끔하게 제공
- 면접 narrative: "fixed → agentic 리팩터" 자체가 서사

**설계:**
- Single agent + 5 tools (`write_pseudo_ir`, `write_anim_ir`, `write_manim_code`, `render_video`, `score_with_vision_qa`)
- IntentTracker 사이드 컴포넌트 (user request에서 entity/operation 추출, 매 turn 후 artifact에서 보존 체크)
- max 25 turns, $1/case cost cap, "critical concept lost" 3회 연속 시 종료

### 3-3. VCR / 캐싱: 없음 (★ 변경)

- 원래 plan은 OpenAI VCR 자체 구현 (15주 플랜 Week 1 우선순위였음)
- **Pivot 후 결정: 스킵.** 이유:
  - 6주 × 16-36 케이스 × ~5 run = 총 OpenAI 비용 추정 $50-100
  - 개인 포트폴리오 프로젝트에 감당 가능
  - VCR 자체 구현은 1주+ 일, 그 시간을 v2 리팩터에 투자
- **주의:** Experiment B (v1 vs v2) 시 같은 goldset으로 돌리므로 OpenAI 호출 중복 발생. 이건 받아들임.
- **cost guard:** 각 run 전에 dry-run으로 호출 수 × 예상 cost 계산, $20/run 초과 시 경고

### 3-4. GIFPT 본체 수정 범위: 최소

**Phase 0-1 (Week 1-3):**
- LangSmith SDK 추가 + trace wrapper 1곳 (`llm_codegen.py`의 OpenAI client 호출부)
- 그 외 v1 코드 무수정

**Phase 2 (Week 4-5):**
- 새 모듈 `GIFPT_AI/studio/v2/` 추가 (Claude Agent SDK + 5 tools + IntentTracker)
- 기존 v1 경로와 병렬 존재. `route=v2` 파라미터로 분기.
- Week 5 말에 v2가 v1 edge metric을 이긴다면 default route를 v2로 전환 검토

---

## 4. 6주 Phase 플랜

### Phase 0 — 진단 + 인프라 (Week 1)

**목적:** v1 baseline 측정 + LangSmith 세팅 + narrative 3 문서.

**산출물:**
- `gifpt/docs/failure-taxonomy.md` — `failure_audit.py` 6-stage → edge 원인 매핑, weekly_audit 실패 20개 수동 분류
- `gifpt/docs/v1-baseline-report.md` — 16 seed × stage pass/fail + edge preservation fail 수동 카운트 (숫자 한 장)
- `gifpt/docs/edge-first-measurement.md` — 3 axiom + GIFPT edge 증거 4개 + build-vs-buy 스파이크 결과 링크
- LangSmith project 세팅 + GIFPT trace integration (`langsmith` SDK, client wrapper)
- Goldset v0 업로드 (16 seeds)

**Gate 1:** 3 문서 사용자 승인 → Phase 1 착수.

**Week 1 말 면접 Ready 라인 1:**
> "v1을 edge-first로 해부했고, LangSmith 위에 측정 인프라 세팅 완료. 다음은 edge preservation evaluator 구현."

### Phase 1 — Edge Evaluators + 실험 A (Week 2-3)

**Week 2 — Edge evaluator 4개 구현**

LangSmith `RunEvaluator` 서브클래스 4개:

1. **`pseudo_anim_preservation.py`** — pseudo_ir → anim_ir edge
   - Schema: Pydantic `AnimIR` 검증
   - Preservation: pseudo_ir의 entity 수와 anim_ir의 layout node 수 비교 (drift > 20% fail)
   - Judge: "anim_ir이 pseudo_ir의 모든 핵심 operation을 포함하는가?" Korean rubric

2. **`anim_codegen_preservation.py`** — anim_ir → codegen edge
   - Schema: AST parse 성공
   - Preservation: anim_ir action 수 vs codegen에서 참조된 helper 수
   - Judge: "codegen이 anim_ir의 의도를 모두 표현하는가?"

3. **`codegen_render_preservation.py`** — codegen → render edge
   - Schema: FORBIDDEN AST list 통과
   - Preservation: `post_process_manim_code`가 실제로 수정한 개수 (높을수록 handoff 누수)
   - `_UNKNOWN_HELPERS` 발생 여부

4. **`render_qa_preservation.py`** — render → qa edge
   - Schema: mp4 valid + duration 정상 범위
   - Preservation: frame count 정상
   - Judge: QA 결과에서 도메인 페널티 발동 여부

**Week 3 — 실험 A (baseline + PEDAGOGICAL_RULES_CONDENSED)**

- LangSmith Evaluation run #1 — `PEDAGOGICAL_RULES_FULL` × goldset v0.5 (16 seed + 20 production failure 합쳐 36)
- LangSmith Evaluation run #2 — `PEDAGOGICAL_RULES_CONDENSED` × goldset v0.5
- LangSmith UI에서 diff 확인 + `langsmith` SDK로 데이터 추출 후 Jinja2 HTML 리포트 생성
- 4차원 벡터 확보: `{기존 실패 감소, 새 실패 등장, 토큰 델타, 도메인별 회귀}`
- `gifpt/docs/snapshots/experiment-a.md` 박제

**Gate 2:** 실험 A diff 리포트 + 4차원 벡터 수치 → Phase 2 착수.

**Week 3 말 면접 Ready 라인 2:**
> "v1에 edge preservation evaluator 4개를 LangSmith custom code로 붙였고, 첫 prompt 실험에서 CONDENSED가 X 개선 Y 회귀 벡터로 나왔습니다. 다음은 v2 agentic loop 리팩터."

### Phase 2 — GIFPT v2 + 실험 B + Judge Calibration (Week 4-5)

**Week 4 — v2 스켈레톤 + 1 케이스 통과**

- `GIFPT_AI/studio/v2/` 모듈 생성
- Claude Agent SDK 통합 (`claude-agent-sdk` Python package)
- 5 tools 정의 + v1 validator 이식 (`qa.py`, `video_render.py` FORBIDDEN, `post_process_manim_code`는 tool 내부로)
- `IntentTracker` 구현 (extract + check)
- Agent system prompt 간소화 (PEDAGOGICAL_RULES만 유지, Manim API ref는 tool docstring으로 이동)
- 1 케이스 end-to-end 통과 (LangSmith trace 포함)
- v2 route 분기 추가 (`route=v2` 파라미터)

**Week 5 — v2 full run + 실험 B + Judge calibration**

- v2 full run on goldset v0.5 (36 case)
- LangSmith evaluation #3: v2 결과를 4개 edge evaluator에 통과
- **실험 B — v1 vs v2 edge-level diff**
  - 같은 goldset, 같은 evaluator
  - 기대: `anim_ir → codegen` edge preservation fail이 v2 `intent_check` turn으로 교정됨
- **Judge self-calibration** ★
  - 사용자(우태호)가 20 golden edge 수기 라벨링 (✓ 정보 보존 / ✗ 누수)
  - `pseudo_anim_preservation` judge 실행 → 20 golden과 agreement 계산
  - ≥ 85% 미달 시 rubric 재튜닝 → 재측정
  - `gifpt/docs/judge-calibration-report.md` 작성
- `gifpt/docs/snapshots/experiment-b.md` 박제

**Gate 3:** Judge agreement ≥ 85% → Phase 3 착수.
**Gate 4 (optional):** v2가 v1 대비 edge preservation fail rate 30% 이상 감소 → default route v2 전환 검토.

### Phase 3 — 리플렉션 + 블로그 + 면접 준비 (Week 6)

- **블로그 1편** (Velog): "Edge-first 측정으로 GIFPT를 해부하고 agentic loop으로 리팩터한 경험"
  - 구조: 문제(프롬프트 엔지니어링 한계) → 측정 재정의(delta over quality) → edge-first → LangSmith + 4 evaluator → v2 결과 벡터 → 교훈
- **이력서 업데이트** — GIFPT 프로젝트 섹션에 "Measurement-Driven Refactor" 항목 추가
- **면접 연습** — 30초 pitch + 보조 질문 대응 (§6 참조)
- (선택) GitHub gist로 4 edge evaluator 코드 공개 (공공재 contribution)
- `gifpt/docs/snapshots/` 아래 실험 박제 3개 정리 (A/B + calibration)

### 버퍼 (Week 7-8)

- 발견된 버그 / rubric 개선
- 면접 실전
- (선택) 실험 C — v2 codegen model 3-way A/B (gpt-4o / gpt-4.1 / claude-sonnet-4-6). 시간 남으면.

---

## 5. GIFPT v2 아키텍처 상세 (Level 2)

### 5-1. 왜 Level 2인가

v1의 9개 실패 패턴 중 6개가 "단계 내 재시도 + tool 사용"으로 풀리는 것. self-heal loop, AST 재검증, color 정규화 전부를 agent turn으로 통합하면 `llm_codegen.py:699-755` self-heal + `:587-649` QA feedback loop 두 덩어리가 사라짐.

Level 3 (Planner-Executor-Critic 3 agent)는 과함 — 6주 scope에 과부하.

### 5-2. 에이전트 구조

```
┌─────────────────────────────────────────────────────────┐
│  GIFPT v2 Agent (Claude Agent SDK, single loop)        │
│  System prompt: "You are an algorithm visualization     │
│  engineer. Produce a Manim video that correctly         │
│  animates the user's request."                          │
│                                                         │
│  Tools:                                                 │
│    write_pseudo_ir(json)   — Pydantic validator        │
│    write_anim_ir(json)     — Pydantic validator        │
│    write_manim_code(py)    — AST validator + post-     │
│                               process (21 color + 9    │
│                               helper regex 내부화)       │
│    render_video()          — Manim subprocess, returns │
│                               frames + log + errors    │
│    score_with_vision_qa()  — Vision QA on frames,      │
│                               returns issues list      │
│                                                         │
│  Side-component: IntentTracker                          │
│    - 시작 시 user request → entity/operation 추출      │
│    - 매 tool 호출 후 artifact의 intent 보존 체크        │
│    - 누락 시 agent에게 "lost concept: X" 피드백         │
│                                                         │
│  Termination:                                           │
│    - finalize + Vision QA score ≥ threshold            │
│    - max 25 turns                                       │
│    - total cost ≥ $1.00 / case                         │
│    - "critical concept lost" 3회 연속                   │
└─────────────────────────────────────────────────────────┘
```

### 5-3. v1 자산 매핑

| v1 위치 | v2에서 | 변환 |
|---|---|---|
| `llm_pseudocode.py` | `tool: write_pseudo_ir` validator | 보존 (Pydantic 그대로) |
| `llm_anim_ir.py` | `tool: write_anim_ir` validator | 보존 |
| `llm_codegen.py` system prompt (200줄) | agent system prompt (축소) | 축소 — PEDAGOGICAL_RULES만 유지, Manim API ref는 tool docstring |
| `video_render.py` FORBIDDEN AST list | `tool: write_manim_code` validator | 보존 |
| `post_process_manim_code` 21 color + 9 helper regex | `tool: write_manim_code` 내부 후처리 | 보존 (v2 Phase 1) |
| `qa.py` 도메인 페널티 | `tool: score_with_vision_qa` return | 보존 |
| `llm_codegen.py:699-755` self-heal loop | 제거, agent의 `revise_manim_code` turn으로 흡수 | **제거** ★ |
| `llm_codegen.py:587-649` QA feedback loop | 제거, agent turn으로 흡수 | **제거** ★ |

### 5-4. IntentTracker 간단 스펙

```python
# GIFPT_AI/studio/v2/intent_tracker.py
@dataclass
class Intent:
    concept: str       # 'compare', 'swap', 'two_pointers', ...
    priority: str      # 'critical' | 'important' | 'nice_to_have'
    source: str        # 'user_request' | 'pseudo_ir' | ...

class IntentTracker:
    def __init__(self, user_request: str, llm_client):
        self.intents = self._extract(user_request, llm_client)
        self.check_history: list[dict] = []

    def _extract(self, req: str, llm) -> list[Intent]:
        # 작은 LLM 호출로 user request에서 operational concept 추출
        ...

    def check(self, stage_name: str, artifact: dict) -> list[str]:
        """artifact에서 어느 intent가 사라졌는지 반환"""
        ...
```

**LangSmith 연동:** IntentTracker의 `lost` 리스트가 해당 edge evaluator의 `preservation_pass=False` + `judge_reason`에 매핑. v2는 루프 안에서 교정, v1은 끝까지 못 봄 → 두 run diff에서 "의미 누수 감소"가 메트릭으로 드러남.

---

## 6. 면접 Narrative (pivot 후 정식 버전)

### 30초 pitch

> "제 GIFPT 프로젝트 — 4-stage LLM 영상 생성 파이프라인 — 가 프롬프트 엔지니어링 한계에 도달했을 때, 두 가지를 알아챘습니다.
>
> 첫째, **영상 품질은 단일 숫자로 측정 불가능합니다.** 그래서 quality 측정을 포기하고 run-to-run delta 측정으로 문제를 재정의했습니다.
>
> 둘째, 측정의 최소 단위는 stage가 아니라 **edge(단계 간 handoff)** 입니다. 실제로 GIFPT 실패의 대부분 — `_UNKNOWN_HELPERS`, LSM-Tree 오분류, 21개 color regex 수작업 덮기 — 가 모두 handoff 누수였습니다.
>
> **LangSmith 위에 edge preservation evaluator 4개를 custom code로 얹어** v1을 해부했고, 측정 결과를 보고 v2를 Claude Agent SDK 기반 single agentic loop + IntentTracker로 리팩터했습니다.
>
> 소유자(본인)가 `scripts/README.md`에 'CI regression tests are a separate piece of work'라고 써둔 그 문장을 — tool을 짓는 대신 LangSmith로 구현한 겁니다."

### 한 줄 버전

> "저는 tool 만드는 사람이 아니라, 제 시스템을 측정 기반으로 개선하는 사람입니다. LangSmith로 GIFPT를 edge 단위로 해부했고, 측정 결과가 v2 리팩터의 의사결정 근거였습니다."

### 보조 질문 대응

| 질문 | 답 |
|---|---|
| **"왜 promptfoo / Inspect AI 말고 LangSmith?"** | "Day 0에 네 도구를 확인했습니다. Promptfoo는 tool sequence만 체크, Inspect AI는 research framework라 CI ergonomics가 약합니다. LangSmith가 run diff + golden set + CI 통합이 가장 성숙했습니다. 그 위에 handoff preservation은 아무 도구에도 없어서 custom evaluator로 직접 만들었습니다." |
| **"왜 edge preservation 도구를 따로 만들지 않았나?"** | "15주 도구 빌드 vs 6주 GIFPT 개선을 놓고 재봤을 때, 저는 tool vendor가 아니라 application engineer입니다. 제 시스템을 고치는 쪽이 목적에 맞았고, LangSmith가 80%를 처리하니 남은 20%만 custom으로 얹었습니다. NIH (Not Invented Here) 함정을 피했다고 생각합니다." |
| **"quality를 측정 안 하면 어떻게 좋아졌는지 아나?"** | "단일 숫자는 거짓말입니다. 4차원 벡터로 보고합니다: 기존 실패 감소, 새 실패 등장, 토큰 델타, 도메인별 회귀. 이 벡터가 실제 의사결정을 가능하게 했고, v2 default route 전환 여부도 이 벡터로 결정했습니다." |
| **"LLM judge도 틀릴 수 있지 않나?"** | "맞습니다. 그래서 20개 golden edge로 agreement ≥ 85% calibrate했고, 미달이면 rubric 재튜닝합니다. 자기 메트릭을 불신할 줄 아는 게 측정 규율의 핵심이라고 생각합니다." |
| **"v2가 실제로 v1보다 좋은가?"** | "실험 B 결과 벡터로 답하면 — [실제 수치 삽입]. 어떤 edge에선 개선, 어떤 edge에선 회귀. 전체 production default를 v2로 바꿀지는 [구체적 수치]로 결정했습니다." |

---

## 7. 열린 결정사항 — Day 1 확정 (2026-04-12)

| # | 질문 | 결정 | 반영 위치 |
|---|---|---|---|
| **A** | GIFPT v2 Agent SDK | **Claude Agent SDK** — 단일 agentic loop + 5 tools | §5 Phase 2 Week 4 |
| **B** | Goldset 확장 시점 | **Week 3** — 실험 A (16 case) 이후 failure 20개 승격 → v0.5 36 case | §5 Phase 1 Week 3 |
| **C** | Judge golden 수기 라벨 | **Week 4** — v2 스캐폴드 완성 후, calibration 직전 | §5 Phase 2 Week 5 |
| **D** | v2 default route 스위칭 기준 | **Edge preservation fail rate −30% 이상** (IntentTracker 효과 직접 측정) | §5 Phase 3 Week 6 |
| **E** | Blog 공개 시점 | **연기** — Week 6 완성 후 Phase 2 수치를 보고 결정 | §5 Phase 3 / 버퍼 |

---

## 8. 리스크 등록

| 리스크 | 가능성 | 완화 |
|---|---|---|
| 6주 플랜 슬립 | 중 | Week 1 Phase 0 문서 3개가 면접 Ready 라인 1 보험. 슬립해도 narrative 있음. |
| LangSmith custom evaluator API 제약 | 중 | Week 2 초반에 1개 evaluator PoC로 검증. 막히면 LangSmith SDK 직접 호출 + 자체 orchestrator로 전환. |
| OpenAI 비용 예상 초과 ($100+) | 낮음 | 각 run 전 dry-run 계산 + $20/run cap. 초과 시 goldset 축소. |
| v2 Claude Agent SDK API breaking change | 낮음 | SDK 버전 핀 고정 |
| Judge agreement 70% 미만 (severe) | 중 | Week 5에 드러남. Week 6 버퍼 1주로 흡수. |
| v2가 v1 대비 edge preservation 개선 없음 (예상 반대) | 중 | **이것도 narrative.** "측정 결과 내 가설(agentic loop이 더 나을 것)이 틀렸다는 걸 확인했고, v1 유지로 결정" — 정직한 measurement discipline 증명. 면접에서 오히려 강력. |
| GIFPT 본체에 예상 외 큰 침습 필요 발견 | 낮음 | Phase 0 Week 1에 trace wrapper 1곳만 수정. 그 외 무수정 원칙. |

---

## 9. 다음 에이전트 실행 지침

### 읽는 순서
1. §0 TL;DR — 30초
2. §2 3 Axioms — 프로젝트 정체성, 외울 것
3. §7 열린 결정사항 5개 — Day 1에 사용자 질의
4. §4 Phase 플랜 — 매일 참조
5. `plan.md` — 주차별 체크리스트

### Day 0 (완료)
- ✓ Build-vs-Buy 스파이크 (`gifpt/docs/build-vs-buy-spike.md`)
- ✓ Pivot 결정 (LangSmith + GIFPT v2)

### Day 1 (완료)
- ✓ §7 4개 결정 확정 (A/B/C/D), E는 Week 6 연기
- ✓ 이 문서 §7 업데이트 + plan.md Day 1 섹션 업데이트

### Week 1 Phase 0 (진행 중)
- [ ] LangSmith account 생성 + project 세팅
- [ ] 3 산출물: failure-taxonomy.md, v1-baseline-report.md, edge-first-measurement.md
- [ ] Goldset v0 (16 case) LangSmith upload
- [ ] GIFPT 파이프라인 @traceable 주입 (5지점)

### 절대 하지 말 것
- 3 Axiom 흔들기 (프로젝트 정체성 손실)
- Harness CI 같은 독립 도구 빌드 — 이미 기각됨
- GIFPT 본체에 대규모 침습 (Phase 0-1에선 trace wrapper 1곳만)
- LangSmith 고급 기능에 scope 확장 (prompt hub, playground 등 무관)
- 오픈소스 공개를 Phase 3 전에 commit
- Phase 2를 Phase 1보다 먼저 시작

### 반드시 할 것
- 각 Phase Gate에서 사용자 확인 후 다음 Phase 진입
- 실험 결과는 `gifpt/docs/snapshots/`에 박제
- Judge rubric은 사용자 review 필수 (Week 4 초안, Week 5 calibration)
- 주간 금요일 self-check: "지금 면접 보면 narrative 성립?" (Week 1부터 Yes여야 함)
- Phase 0 3 문서는 **GIFPT 리포에** commit (이 프로젝트의 정식 산출물)

---

## 10. GIFPT 리포 참고 경로

| 파일 | 라인 | 내용 |
|---|---|---|
| `GIFPT_AI/studio/tasks.py` | — | Celery entry `animate_algorithm` |
| `GIFPT_AI/studio/video_render.py` | 68-84 | AST FORBIDDEN list |
| `GIFPT_AI/studio/video_render.py` | 307-317 | LSM-Tree 오분류 docstring |
| `GIFPT_AI/studio/ai/llm_codegen.py` | 29-30 | `MODEL_PRIMARY` / `MODEL_FAST` |
| `GIFPT_AI/studio/ai/llm_codegen.py` | 34-99 | `PEDAGOGICAL_RULES_FULL/CONDENSED` |
| `GIFPT_AI/studio/ai/llm_codegen.py` | 409-425 | 21 forbidden color regex |
| `GIFPT_AI/studio/ai/llm_codegen.py` | 427-433 | `_UNKNOWN_HELPERS` |
| `GIFPT_AI/studio/ai/llm_codegen.py` | 436-506 | `post_process_manim_code` |
| `GIFPT_AI/studio/ai/llm_codegen.py` | 587-649 | QA feedback loop |
| `GIFPT_AI/studio/ai/llm_codegen.py` | 699-755 | self-heal loop |
| `GIFPT_AI/studio/ai/qa.py` | 275-342 | 도메인 페널티 |
| `GIFPT_AI/studio/ai/examples/seed_examples.jsonl` | — | 16 seeds |
| `GIFPT_AI/scripts/failure_audit.py` | — | 6-stage taxonomy |
| `GIFPT_AI/scripts/seed_audit.py` | — | 16 seed QA |
| `GIFPT_AI/scripts/weekly_audit.py` | — | 주간 fail rate |
| **`GIFPT_AI/scripts/README.md`** | **103-104** | **"CI regression tests are a separate piece of work..." narrative 인용문** |

---

## 11. 용어집

| 용어 | 의미 |
|---|---|
| **Delta over quality** | 절대 품질 측정을 포기하고 run-to-run 변화량을 측정한다는 원칙 (Axiom 1) |
| **Edge / handoff** | agent N의 출력이 agent N+1의 입력으로 넘어가는 순간. 측정의 제1 단위 (Axiom 2) |
| **Edge integrity** | 한 edge에 대한 4종 assertion (schema, preservation, judge, attribution) 통과 여부 |
| **Edge preservation evaluator** | LangSmith custom code evaluator로 구현된 edge integrity 체크 로직 4개 (pseudo→anim, anim→codegen, codegen→render, render→qa) |
| **Goldset** | 고정 입력 집합. v0 = 16 seed, v0.5 = + 20 weekly audit 실패 |
| **IntentTracker** | GIFPT v2에서 user request의 핵심 개념이 매 turn 후 artifact에 보존되는지 체크하는 컴포넌트 |
| **Level 2** | single agentic loop + tools + IntentTracker. GIFPT v2 아키텍처 |
| **Judge self-calibration** | LLM judge 출력을 20 golden edge와 agreement 측정. ≥85% 미달 시 rubric 재튜닝 |
| **Measurement-driven refactor** | 이 프로젝트의 정체. "측정 없이 리팩터 안 한다"는 원칙을 GIFPT v1 → v2에 적용 |
| **면접 Ready 라인** | Week 1 말 (Phase 0 완료), Week 3 말 (실험 A 완료), Week 5 말 (v2 완료) 세 지점 |

---

*문서 끝. `plan.md`로 이동해 Week 1 Day 1부터 시작.*
