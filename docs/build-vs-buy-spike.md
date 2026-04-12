# Build-vs-Buy Spike — LLM Pipeline Regression Testing Tools

> **작성일:** 2026-04-12
> **작성 시간:** 약 15분 (WebSearch + 공식 문서 fetch)
> **목적:** Harness CI를 직접 만드는 의사결정의 물증 확보. 기존 도구(promptfoo / Inspect AI / LangSmith / Weave)가 edge-level preservation diff를 이미 제공한다면 자체 빌드는 정당화되지 않는다.
> **판정:** **Go, 단 narrative 조정 필요.** 자체 빌드는 정당하지만 "공백 포지션" 프레이밍은 부정확하다.

---

## 0. TL;DR

1. **4개 도구 모두 multi-step agent 평가를 어느 정도 지원**한다. "아무도 안 만들었다"는 원래 가정은 **틀렸다**.
2. **그러나 4개 중 어느 것도 "handoff에서의 의미 보존(semantic preservation at handoff)"을 측정 primitive로 삼지 않는다.** Tool call sequence, step count, trace view는 있어도 "stage N의 entity 5개가 stage N+1에 4개만 살아남았다"를 1st-class assertion으로 다루는 도구는 없다.
3. **LangSmith가 가장 가까운 경쟁자**다. Run-over-run diff, side-by-side comparison, CI/CD 통합, golden set 기반 regression — 대부분의 Harness CI 기능이 이미 있거나 custom evaluator로 2주 안에 달성 가능.
4. **결정: Go.** 자체 빌드 진행. 단, 면접 narrative에서 "공백 포지션"이라고 말하면 거짓이다. 대신 **"edge-first measurement discipline이 distinguishing insight이고, 이를 data model primitive로 올린 도구는 없다"** 로 프레이밍을 좁혀야 한다.
5. **주의:** Phase -1의 대안 루트(LangSmith + custom evaluators 2주)가 실제로 존재한다. Phase 1 Week 3 이후 구현 난이도가 예상보다 높게 나오면, 이 대안으로 전환하는 것을 진지하게 고려할 것.

---

## 1. 도구별 조사 결과

### 1-1. promptfoo

**공식 trajectory assertion 4종** (출처: `docs/configuration/expected-outputs/deterministic/#trajectory-assertions`):

| Assertion | 측정 대상 |
|---|---|
| `trajectory:tool-used` | 특정 tool이 호출됐는가 (min/max 카운트 지원) |
| `trajectory:tool-args-match` | Tool call 인자가 기대값과 일치하는가 (partial/exact) |
| `trajectory:tool-sequence` | Tool 호출 순서 (exact / in-order) |
| `trajectory:step-count` | 정규화된 step 수 (tool, command, search, reasoning, message, span 필터) |

**측정하지 않는 것:**
- ❌ Semantic preservation (entity count, intent consistency)
- ❌ Information fidelity across handoffs
- ❌ Inter-stage output quality
- ❌ v1 vs v2 trajectory diff (**run 간 비교 기능 없음**)

**Regression 지원:** 단일 run을 "expected 패턴"에 대한 assertion으로 검증하는 방식. **Run-over-run 비교는 공식 문서에 없음.**

**결론:** Promptfoo는 "프롬프트 × 모델 × 테스트 케이스" 매트릭스 도구에 trajectory 개념을 얹은 것. **Structural validation only.** GIFPT의 실제 실패(의미 누수)는 promptfoo로 감지 불가.

### 1-2. Inspect AI (UK AISI)

**강점:**
- `handoff()` primitive — multi-agent 간 전체 대화 히스토리 전달
- `@subtask`, `transcript` — 상세한 trajectory observability
- `TaskState.store` — 단계 간 상태 전달
- `Agent` / `Tool` API가 풍부함 (research-grade)

**한계 (핵심):**
- ❌ `handoff()`는 **orchestration primitive**이지 **measurement primitive가 아님**. 에이전트 간 전환을 수행할 뿐, 그 전환의 semantic fidelity를 측정하지 않음.
- ❌ Scorer는 final output에 작동. Per-step observability는 있으나 "handoff-level score"라는 개념 부재.
- ❌ 공식 문서에 **v1 vs v2 handoff diff 도구 없음**. Log dataframe 분석은 있지만 handoff 단위 change detection은 custom 구현 필요.
- ⚠️ 포지션: CI gate / developer tool이 아닌 **research evaluation framework**. HTML 리포트, GitHub Action, VCR은 제공 안 함.

**공식 문서 인용:** "monitoring semantic preservation or differential handoff behavior appears to be left to custom implementation."

**결론:** Multi-agent 아키텍처 구축은 강하지만, **그 아키텍처에서 발생하는 handoff 누수를 측정하는 것은 사용자 몫**. Harness CI와 상호보완적이지 대체재 아님.

### 1-3. LangSmith (가장 가까운 경쟁자)

**강점 (Harness CI와 겹치는 부분):**
- ✅ **Run-over-run diff** — side-by-side comparison view, "diff run-over-run score changes side by side"
- ✅ **Golden set regression** — "storing a golden set of examples, then ensuring future versions don't degrade scores"
- ✅ **CI/CD 통합** — GitHub Action 지원, "every CI run appears under Experiments grouped by ci-regression prefix"
- ✅ **Per-step evaluation** — "decision-making process" 기반 scoring, "sequence of selected tools"
- ✅ **Multi-step agent tracing** — LangGraph multi-agent workflow 지원
- ✅ **Component evaluation** — "LLM calls, retrieval steps, tool invocations, output formatting" 각각에 quality criteria

**그럼에도 갭이 있는 부분:**
- ❌ **Semantic preservation at handoff이 1st-class 개념 아님.** Component-level evaluation은 있지만 "component A의 출력이 component B에서 의미적으로 보존되었는가"를 asserting하는 기본 primitive는 문서에 없음.
- ❌ Entity/operation count 기반 preservation 체크는 custom code evaluator로 구현 가능하지만 **내장되어 있지 않음**.
- ❌ Edge integrity matrix (행=케이스, 열=edge, 셀=3-check) 같은 UI 없음 — run diff는 trace 단위지 edge 단위 아님.
- ⚠️ SaaS 중심. Self-host 가능하지만 운영 복잡도 있음.
- ⚠️ LangChain ecosystem-coupled. GIFPT는 LangChain 안 씀.
- ⚠️ 가격: 데이터량 × 보관 기간 기반 pricing.

**결정적 인용:** 공식 문서에 "no mention of semantic preservation metrics across agent handoffs (entity count, operation count, intent preservation)." 이건 custom code evaluator로 구현해야 하는 영역.

**대안 루트 — LangSmith + Custom Evaluators (2주):**

만약 LangSmith를 사용한다면:
1. GIFPT의 4-stage를 LangSmith trace로 전송 (1일)
2. Custom code evaluator 4개 작성: pseudo→anim preservation, anim→codegen preservation, codegen→render preservation, render→qa preservation (3~4일)
3. Golden set 업로드 (16 seed + 20 weekly failure) (1일)
4. LangSmith UI에서 run diff, CI Action 설정 (1~2일)
5. 부족한 부분(edge integrity matrix UI, attribution graph)은 LangSmith API로 데이터 fetch 후 Jinja2 한 장 (3~4일)

**총 2주.** Harness CI 풀빌드 대비 13주 절약.

**trade-off:**
- ✅ 13주 절약
- ✅ 이미 성숙한 trace viewer, CI 통합
- ❌ **"내가 만들었다" narrative 손상** — "LangSmith를 썼다"는 평범한 이야기
- ❌ SaaS 의존 (비공개/오프라인 재현 어려움)
- ❌ LangSmith 제약에 묶임 — edge-first data model을 얹기 어려움
- ❌ Dogfood narrative 약해짐 — "본인 도구로 본인 프로젝트를 고쳤다"는 못 씀
- ❌ GIFPT v2 실험(Phase 2)은 여전히 필요 — LangSmith는 평가 도구지 refactor 대상 아님

**이 대안의 의미:** Harness CI 풀빌드가 **기술적으로 필수는 아님**. 면접 narrative와 dogfood 경험이 필요해서 짓는 것. 이걸 정직하게 인정해야 함.

### 1-4. Weave (Weights & Biases)

**강점:**
- ✅ Side-by-side comparison view (2개 객체 비교)
- ✅ "Diff only" 토글로 변경된 row만 필터링
- ✅ Evaluation aggregate score 비교
- ✅ Step-by-step trace (prompts, responses, tool calls, latencies, tokens 자동 캡처)

**한계:**
- ❌ Evaluation comparison은 **aggregate score 기반**. Individual example 드릴다운 가능하지만 per-handoff preservation은 없음.
- ❌ 공식 커뮤니티 포럼에 **"Feature Request: Head-to-head comparisons for Weave evaluations"** 스레드 존재 — head-to-head 비교 자체가 최근까지 feature request였음.
- ❌ Edge integrity / preservation assertion 개념 없음.
- ⚠️ W&B ecosystem 중심, ML training run 통합이 주목적.

**결론:** LangSmith보다 LLM eval 성숙도가 낮고, edge-level diff는 **더 멀다**. 경쟁자 후보에서 제외.

---

## 2. 실제 갭 (honest gap analysis)

| 요구사항 | promptfoo | Inspect | LangSmith | Weave | Harness CI 목표 |
|---|---|---|---|---|---|
| Multi-step agent 실행 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Trace / trajectory 관찰 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Run-over-run diff | ❌ | ❌ | ✅ | ⚠️ | ✅ |
| Golden set regression | ✅ | ✅ | ✅ | ✅ | ✅ |
| CI 통합 (GitHub Action) | ✅ | ⚠️ | ✅ | ⚠️ | ✅ |
| Self-host | ✅ | ✅ | ⚠️ | ⚠️ | ✅ |
| **Semantic preservation at handoff (1st-class)** | ❌ | ❌ | ❌ | ❌ | **✅ ★** |
| **Edge integrity matrix UI** | ❌ | ❌ | ❌ | ❌ | **✅ ★** |
| **Attribution graph (failure → origin edge)** | ❌ | ❌ | ❌ | ❌ | **✅ ★** |
| **Handoff 레벨 LLM-judge + calibration** | ❌ | ❌ | ⚠️ (custom) | ❌ | **✅ ★** |
| Dynamic-ready data model (Level 0/2/3) | ❌ | ⚠️ | ❌ | ❌ | **✅ ★** |

★ 5개가 Harness CI의 distinguishing primitives. **이게 진짜 갭이다.**

**객관적 판단:** 5개 중 처음 4개(semantic preservation, edge integrity matrix, attribution graph, handoff judge)는 **LangSmith에 custom code evaluator로 2주 내 구축 가능.** 구조적으로 불가능한 게 아니라 **아무도 아직 만들지 않은 것**이다.

5번째(dynamic-ready data model)만 **진짜 구조적 갭**이다. LangSmith의 run/step 모델은 fixed trace 형태라 Level 2(agent loop, variable turn count)를 자연스럽게 담지 못함. 이건 LangSmith에 custom으로 얹기 어려움.

---

## 3. 의사결정 프레임워크

### 3-1. 순수 기술 관점

**가장 합리적 선택: LangSmith + custom evaluators (2주)**

- 기술 갭의 80%를 2주에 메꿈
- 13주 절약
- 성숙한 UI / CI 통합 재사용
- GIFPT v2 실험에 집중할 수 있음

### 3-2. 면접 narrative 관점

**가장 합리적 선택: Harness CI 자체 빌드 (15주)**

- "LangSmith를 썼다"는 면접에서 평범한 이야기
- "내가 만들었다 + 내 프로젝트를 고쳤다" dogfood narrative는 강력
- `scripts/README.md:103-104` 인용문이 살아남음
- Edge-first data model을 "내가 정의했다"로 팔 수 있음
- 시니어 engineering discipline narrative (§1 플랜의 3 axiom) 전체가 작동

### 3-3. 두 관점의 충돌 해소

**권장: 자체 빌드 (narrative 우선), 단 정직하게**

이유:
1. 이 프로젝트의 목적은 **LLM eval 업계에 새 도구 공급**이 아니라 **본인 포트폴리오 + 면접 narrative**다. LangSmith 사용자가 되는 건 목적 달성에 부족하다.
2. 기술적으로 "필수는 아니지만 의미 있다"가 정확한 표현. 이걸 면접에서 **숨기지 말 것**. "LangSmith로도 60% 가능하지만 edge-first data model을 1st-class로 삼으려면 직접 만들어야 했다" 가 honest framing.
3. Dogfood 경험(GIFPT v2 리팩터) 자체가 narrative의 핵심이고, 이건 어느 도구를 쓰든 해야 함. Harness CI 빌드는 dogfood 경험을 **더 풍부하게** 만드는 수단이지 독립 목표 아님.

**주의 — narrative 조정 필수:**

원래 플랜(`harness-ci-plan-v2.md §1`)의 "공백 포지션" 표현은 **부정확하다.** 면접에서 이렇게 말하면 안 됨:

❌ "아무도 multi-stage LLM pipeline regression testing을 만들지 않았습니다."
→ LangSmith가 반박 가능. 거짓말로 들림.

✅ "LangSmith가 multi-stage regression testing을 잘 합니다. 하지만 **handoff 자체를 1st-class measurement primitive로 올린 도구는 없습니다.** 저는 edge를 data model의 기본 단위로 설계했고, 이게 Level 0/2/3 trajectory를 같은 스키마로 저장하는 걸 가능하게 합니다. 이 차이가 GIFPT v2 리팩터에서 의미 있었던 이유는..."

이 버전이 **방어 가능하고 정확**하다.

---

## 4. Go/No-Go 판정

### 판정: **Go** (자체 빌드 진행)

### 조건부 — narrative 업데이트 필요

`harness-ci-plan-v2.md`와 `harness-ci-narrative.md`에 다음 수정 사항을 반영:

1. **§4 경쟁 지형 표 수정** — LangSmith를 "공백 포지션"이 아닌 "가장 가까운 경쟁자"로 재분류. LangSmith에 custom code evaluator를 추가하면 80% 달성 가능함을 인정.
2. **§8 면접 narrative에서 "공백 포지션" 표현 삭제** — "handoff를 1st-class measurement primitive로 올린 데이터 모델"로 대체.
3. **§12 보조 질문 대응에 "LangSmith로 안 됐나?" 추가** — "LangSmith custom evaluator 2주로 60%는 가능했습니다. 하지만 dynamic-ready data model과 dogfood 경험을 위해 자체 빌드 선택했고, 이 선택은 trade-off가 명확했습니다" 형태의 정직한 답변.
4. **§11 열린 결정사항에 질문 추가** — "narrative 조정 후에도 자체 빌드 진행하시겠습니까?" (사용자 최종 confirm)

### 변경 없는 부분

- 3 axiom (delta / edge-first / dynamic graph) 유지 — LangSmith 조사 결과로도 흔들리지 않음
- 15주 Phase 플랜 유지
- Phase 0 narrative 산출물 계획 유지
- SQLite 스키마, Adapter protocol, VCR 설계 유지
- GIFPT v2 Level 2 아키텍처 유지

### Abort 조건

다음이 발견되면 재검토:
- ❗ LangSmith에 "edge preservation assertion"이 공식 기능으로 추가됨 (현재 없음)
- ❗ Inspect AI에 handoff-level scorer 정식 추가됨 (현재 없음)
- ❗ Phase 1 Week 4까지 `run_case()` 1케이스 통과 실패 → LangSmith 대안 재고려

---

## 5. 사용자 최종 confirm 필요

다음 3개 질문에 답한 후 Phase 0 착수:

1. **Narrative 조정 동의?** — "공백 포지션" 대신 "가장 가까운 경쟁자 LangSmith, 갭은 edge-first data model primitive"로 재프레이밍.
2. **Trade-off 수용?** — 13주 더 쓰는 대가로 자체 빌드 narrative + dogfood 경험 확보. 반대로 LangSmith 루트는 2주에 60% + 평범한 narrative.
3. **LangSmith 면접 방어 답변 준비?** — 면접관이 "LangSmith로는 안 됐나?"를 물을 때 정직하게 "60%는 됐습니다, 하지만 X 때문에 직접 지었습니다"를 말할 준비가 되어 있는가? (Y/N)

**셋 다 Y면 Phase 0 착수. 하나라도 N이면 재논의.**

---

## 6. Sources

### 공식 문서
- [Promptfoo Deterministic Assertions (trajectory section)](https://www.promptfoo.dev/docs/configuration/expected-outputs/deterministic/#trajectory-assertions)
- [Promptfoo main docs](https://www.promptfoo.dev/docs/getting-started/)
- [Inspect AI Multi-Agent](https://inspect.aisi.org.uk/multi-agent.html)
- [Inspect AI Using Agents](https://inspect.aisi.org.uk/agents.html)
- [Inspect AI main](https://inspect.aisi.org.uk/)
- [LangSmith Evaluation Concepts](https://docs.langchain.com/langsmith/evaluation-concepts)
- [LangSmith Platform Overview](https://www.langchain.com/langsmith/evaluation)
- [Weave Comparison](https://weave-docs.wandb.ai/guides/tools/comparison/)
- [W&B Weave main](https://docs.wandb.ai/weave)

### 분석 / 비교 글
- [LangSmith CI/CD Integration: Automated Regression Testing 2026](https://markaicode.com/langsmith-cicd-automated-regression-testing/)
- [Best Promptfoo alternatives in 2026 (Braintrust)](https://www.braintrust.dev/articles/best-promptfoo-alternatives-2026)
- [5 best prompt engineering tools 2026 (Braintrust)](https://www.braintrust.dev/articles/best-prompt-engineering-tools-2026)
- [Top 5 Prompt Engineering Platforms in 2026 (Maxim AI)](https://www.getmaxim.ai/articles/top-5-prompt-engineering-platforms-in-2026-3/)
- [Weave Feature Request: Head-to-head comparisons (W&B Community)](https://community.wandb.ai/t/feature-request-head-to-head-comparisons-for-weave-evaluations/7109)

*문서 끝. 사용자 §5 confirm 후 Phase 0 (Week 1) 착수.*
