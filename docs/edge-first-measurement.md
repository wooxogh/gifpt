# Edge-First Measurement — 왜 stage가 아닌 handoff인가

> **작성일:** 2026-04-12
> **목적:** GIFPT v2 refactor의 **측정 철학**을 선언. Phase 0 산출물 3/3.
> **앵커:** `GIFPT_AI/scripts/README.md:103-104`
> **좌표:** `gifpt-measurement-driven-refactor.md` canonical plan의 §2 "3 Axioms" 전개.

---

## 0. Anchor Quote

> *"Not a CI gate. These run locally. **CI regression tests are a separate piece of work that will eventually consume the same `seed_audit.py` machinery.**"*
> — `GIFPT_AI/scripts/README.md:103-104`

이 한 줄이 프로젝트의 출발점이다. "나중에 할 일"로 미뤄뒀던 CI regression 체계를 **지금 측정 규율부터 세우고 v2 refactor에 박제**하는 것이 본 phase의 목표다.

## 1. 3 Axioms

### Axiom 1 — Delta over quality
**"LLM 영상의 절대 품질은 측정 불가능. 그러나 run-to-run **delta**는 측정 가능하고 그것으로 충분하다."**

절대 품질(예: "이 bubble sort 영상은 6.5/10점 가치가 있다")은 측정할 수 없다. 하지만 "prompt를 바꿨더니 16 case 중 5개가 green→red로 전환, cost −40%"는 측정 가능하고 **의사결정 가능한** 정보다.

면접에서의 함의: "내가 v2를 통해 정량 품질이 X% 개선되었다"가 아니라, "내가 측정 규율로 **어떤 변경이 어떤 방향으로 영향을 주는지** 가시화했다"가 올바른 narrative.

### Axiom 2 — Edge-first
**"실패는 stage 안이 아니라 stage 사이에서 발생한다. 측정 단위는 edge(handoff)여야 한다."**

v1의 `post_process_manim_code`가 26개의 regex 규칙으로 치료하는 것은 `anim_ir → codegen` edge에서 정보가 소실된 증상이다. 3단계 LLM 파이프라인에서 각 단계는 보통 나름 합리적인 출력을 낸다 — 문제는 앞 단계가 뒷 단계에 **구조화된 의미를 전달하는 방식**이 부실하다는 것.

따라서 측정 단위는:
- ❌ "codegen stage의 pass rate"
- ✅ "anim_ir의 entity/operation set이 manim_code에 보존되는 비율"

4 edge:

| Edge | From | To | 측정 질문 |
|---|---|---|---|
| `pseudo→anim` | Pseudocode IR | Animation IR | 엔티티/operation/intent가 scene list에 온전히 표현되었나? |
| `anim→codegen` | Animation IR | Manim Code | scene descriptor의 각 객체가 `Create`/`Transform` 호출에 매칭되나? |
| `codegen→render` | Manim Code | mp4 | FORBIDDEN AST 없이 정상 렌더되나? (timeout, NameError, invalid API) |
| `render→qa` | mp4 | QA verdict | 도메인별 required check(comparison_shown, nodes_visible, ...)가 시각적으로 만족되나? |

### Axiom 3 — Dynamic directed graph data model
**"trajectory는 노드(step) + 엣지(handoff)로 이루어진 동적 방향 그래프. 고정 파이프라인은 이 그래프의 degenerate case."**

v1은 "4단계 선형 파이프라인". v2는 Claude Agent SDK 기반의 agentic loop에서 IntentTracker가 **turn마다** 의도 보존을 체크 — 즉 실행 경로가 **런타임에 결정**된다. 같은 측정 스키마(step + edge)로 두 실행 모드를 모두 표현할 수 있어야 한다.

이것이 Level 0(fixed) → Level 2(agentic) → Level 3(planner-executor-critic) 어느 아키텍처를 선택해도 동일한 measurement 기반이 유지된다는 뜻이다.

## 2. 4 Edge Evidence — v1 코드가 이미 말하고 있는 것

(`v1-baseline-report.md §6` 요약 — 이 문서에서는 "왜 이 4개가 axiom의 증명인가"를 강조)

| # | 증거 | Axiom 증명 |
|---|---|---|
| 1 | `_UNKNOWN_HELPERS` 11개 블랙리스트 (`llm_codegen.py:427`) | **Axiom 2** — codegen stage가 문제가 아니라 `anim→codegen` edge에서 scene descriptor가 부실해서 helper가 hallucinate됨. 개발자가 하류에서 블랙리스트로 방어 중. |
| 2 | `_INVALID_COLOR_MAP` 15개 매핑 (`llm_codegen.py:409`) + **`post_process_manim_code`의 26 regex**  | **Axiom 2 + Axiom 1** — 정보 소실은 계속 발생하고(Axiom 2), 각 변경이 이 26 규칙에 미치는 delta를 알아야 pruning 가능(Axiom 1). |
| 3 | `sorting.comparison_shown -2.5` 페널티 (`qa.py:281`) | **Axiom 2** — QA에서 페널티를 부과한다는 것은 `render→qa` edge에서 "의도된 compare 연산"이 영상에 **없다**는 뜻. upstream edge들이 이미 소실된 정보를 하류에서 역추적 검출하는 구조. |
| 4 | LSM-Tree 오분류 → feature 제거 주석 (`video_render.py:311`) | **Axiom 2 + Axiom 3** — `pseudo→anim` edge의 도메인 분류 소실이 production crash로 이어짐 → feature 포기. 측정 도구가 있었다면 분류기를 fix했을 수도 있음. |

이 4개는 v2에서 고쳐야 할 **목표**인 동시에, Phase 0의 narrative 증거다.

## 3. Delta vs Quality 철학

**왜 절대 품질 지표를 만들지 않는가:**

1. **LLM-as-judge는 자기 드리프트.** 같은 모델로 생성하고 같은 모델로 평가하면 편향 누적.
2. **인간 labeling은 scale 안 됨.** 16 case × 4 edge × 매 주 = 사람 불가.
3. **절대 수치는 해석 불가.** "judge score 6.5"는 의사결정 가능한 정보가 아니다. "judge score가 A run에서 6.5 → B run에서 5.8, 이때 downgrade된 case 3개 확인"은 의사결정 가능.

**따라서:**
- 측정의 primary output은 **run diff**다. (LangSmith의 "Compare Runs" 기능이 이 요구와 정렬된 이유.)
- Secondary output은 **4차원 벡터 스냅샷** (pass rate / cost / latency / judge score) — 다른 차원과의 트레이드오프 분석용.
- Tertiary output은 **golden edge self-calibration** — judge가 20개 수기 라벨과 ≥85% agreement 나와야 신뢰.

## 4. 경쟁 지형 — 왜 LangSmith인가 (Build-vs-Buy 결과)

자세한 분석: `build-vs-buy-spike.md`. 요약:

| 도구 | Run diff | Golden set regression | Per-step eval | Edge preservation | 결론 |
|---|:---:|:---:|:---:|:---:|---|
| **promptfoo** | ✓ | ✓ (test cases) | △ (assertions only) | ✗ | Multi-stage trajectory 개념 없음 |
| **Inspect AI (UK AISI)** | ✓ | ✓ | ✓ | ✗ (handoff은 orchestration 개념) | 측정보다 orchestration 우선 |
| **LangSmith** | ✓ | ✓ | ✓ (`@traceable`) | ✗ (built-in 없음) | **Custom code evaluator로 확장 가능** |
| **Weave (W&B)** | △ | ✓ | ✓ | ✗ | head-to-head는 feature request 상태 |

**결정:** LangSmith 채택. `@traceable` 데코레이터로 GIFPT v1에 5지점(`pseudo_ir`, `anim_ir`, `codegen`, `render`, `qa`) trace 주입 → **custom code evaluator 4개**로 4 edge preservation을 직접 측정.

**자체 구축 폐기 이유:**
- LangSmith가 run-over-run diff, golden set regression, CI 통합, per-step evaluation을 이미 제공.
- 미비한 것은 **edge-level preservation assertion**만 — 이건 custom evaluator 4개로 2주 내 구현 가능.
- 자체 도구 빌드는 narrative로는 멋있지만, **"내가 도구를 만들었다" < "내가 기존 도구로 내 시스템을 고쳤다"** 가 실무 narrative로 더 강력하다.

## 5. 4 Custom Code Evaluator 설계 개요

Phase 1 Week 2에 LangSmith SDK로 구현. 각 evaluator는 (run output, example input)을 받아 `{score: 0|1, metadata: {...}}`를 반환.

| Evaluator | 측정 대상 | 입력 | 출력 예시 |
|---|---|---|---|
| `pseudo_anim_preservation` | `pseudo→anim` edge | Pseudocode IR + Animation IR | `{score: 0, missing: ["compare_swap operation"]}` |
| `anim_codegen_preservation` | `anim→codegen` edge | Animation IR + Manim AST | `{score: 0, unmatched_scenes: ["highlight_pivot"], hallucinated_helpers: ["Focus"]}` |
| `codegen_render_preservation` | `codegen→render` edge | Manim AST + render metadata | `{score: 1, forbidden_ast: [], runtime_s: 42}` |
| `render_qa_preservation` | `render→qa` edge | mp4 metadata + QA verdict | `{score: 0, failed_checks: ["comparison_shown", "sorted_progression"]}` |

모든 evaluator는 **deterministic code (LLM 아님)** 로 구현 → cost $0, reproducible. Judge LLM은 Phase 2 Week 5에서 "ambiguous case의 semantic preservation" 판정용으로만 별도 합류.

## 6. Dynamic Graph Data Model 미리보기

v2의 IntentTracker를 위해 trajectory를 다음과 같이 표현:

```
Step: {
  id: "step_3",
  turn: 3,
  tool: "write_manim_code",
  input_hash: "sha256:...",
  output_hash: "sha256:...",
  duration_ms: 2400,
  cost_tokens: {prompt: 850, completion: 1200}
}

Edge: {
  from_step: "step_2",      # anim_ir write
  to_step: "step_3",        # codegen
  kind: "handoff",
  preservation_score: 0.0,  # edge evaluator 출력
  preservation_meta: {
    unmatched_scenes: [...],
    hallucinated_helpers: [...]
  }
}
```

v1의 선형 파이프라인: 4 step + 4 edge (degenerate case).
v2의 agentic loop: step이 반복 가능 (예: `write_manim_code`가 QA feedback을 받고 2번 호출) — trajectory는 더 긴 path, edge 수는 동적.

같은 schema가 두 실행 모드를 모두 표현. 이것이 Axiom 3의 실제 의미.

## 7. Ready Line 1 — 이 문서로 면접 narrative 성립

Phase 0 Week 1 완료 시점에 면접을 본다고 가정하면, 이 3 문서(`failure-taxonomy.md`, `v1-baseline-report.md`, `edge-first-measurement.md`)만으로도 narrative가 성립한다:

> "저는 GIFPT라는 LLM 기반 알고리즘 영상 생성기를 만들었는데, 운영하면서 **측정 도구의 부재**가 계속 발목을 잡았습니다. `post_process_manim_code`에 regex 규칙 26개가 쌓였지만 어느 규칙이 효과적인지 data가 없었습니다. 그래서 Phase 0으로 **edge-first 측정 철학**을 세웠고 — 측정 단위를 stage가 아닌 **handoff edge**로 정의, 절대 품질이 아닌 **run-to-run delta**를 primary output으로, trajectory를 **dynamic directed graph**로 표현 — 이것을 v1 코드 베이스의 4가지 정량 증거로 뒷받침했습니다. 다음 phase에서 LangSmith의 custom code evaluator 4개로 이 철학을 구현하고, GIFPT v2 agentic refactor에 박제할 계획입니다."

## 8. 다음 단계

- [ ] Week 1 말: 3 문서 user review → Gate 1
- [ ] Week 2: LangSmith 세팅 + 4 evaluator 구현 (§5의 계획 실행)
- [ ] Week 3: 실험 A (PEDAGOGICAL_RULES_FULL vs CONDENSED) → 첫 실제 run diff
- [ ] Week 5: 실험 B (v1 vs v2) → edge preservation fail rate 비교

---

**참조:**
- Canonical plan: `.claude/gifpt-measurement-driven-refactor.md`
- Build-vs-buy 결정: `build-vs-buy-spike.md`
- v1 baseline 수치: `v1-baseline-report.md`
- Failure 재분류: `failure-taxonomy.md`
- Anchor: `GIFPT_AI/scripts/README.md:103-104`
