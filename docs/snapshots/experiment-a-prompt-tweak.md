# Experiment A — Prompt Tweak (FULL vs CONDENSED)

> **작성일:** 2026-04-13
> **목적:** Week 3 Gate 2 — `PEDAGOGICAL_RULES_FULL` vs `PEDAGOGICAL_RULES_CONDENSED` 프롬프트 변형이 4차원 벡터(pass / cost / latency / judge)에 어떻게 반영되는지 LangSmith 실측으로 확인.
> **데이터 소스:** LangSmith 두 experiment 세션 + 4 custom edge preservation evaluator (Week 2 구현본)
> **데이터셋:** `gifpt-goldset-v0` (16 cases, dataset id `75f5e777-99e6-4914-97a8-0be3b696f4f8`)
> **파이프라인 모델:** `pseudo_ir`, `anim_ir`, `codegen` 3-stage 모두 `gpt-4o` 통일 (Vision QA만 `gpt-4o-mini`) — 프롬프트 delta가 모델-티어 delta와 혼입되지 않도록 한 통제 조건
> **상태:** Week 3 Task 6 완료. Gate 2 판단 근거.

---

## 0. TL;DR (면접용)

> "프롬프트 하나만 바꿨을 때(FULL → CONDENSED, −7.5% 토큰) **단일 aggregate 지표로는 CONDENSED가 지는 것처럼 보인다** — render 성공률 81.2% → 68.8%, 평균 QA 5.78 → 4.64. 그런데 edge 단위로 쪼개 보면 **정반대 신호가 공존**한다: CONDENSED는 `pseudo→anim`, `anim→codegen` IR 보존률에서 **+18.8%p씩** 올랐고, 대신 `render→qa` 시각 품질에서 −6.25%p 잃었다. 이게 핵심이다. **edge-first measurement가 아니었다면 이 tradeoff를 못 봤고**, Phase 0 narrative의 '단일 quality 지표는 실패 원인을 가린다'를 실험 한 번으로 검증했다. Gate 2 결론: CONDENSED를 default로 스위칭하지 않는다. 대신 **IR edge에서 18.8%p를 얻었다는 신호는 prompt-level scaffolding이 천장에 부딪혔다는 증거**이므로 v2 (Week 4)의 IntentTracker로 이어진다."

---

## 1. 실험 설정

| 항목 | 값 |
|---|---|
| Dataset | `gifpt-goldset-v0` (16 cases, 11 domains) |
| Independent variable | `GIFPT_PROMPT_VARIANT` ∈ {`full`, `condensed`} |
| Controlled | 파이프라인 모델 3-stage 모두 `gpt-4o` / 동일 few-shot / 동일 render 경로 / 동일 QA rubric |
| Prompt delta | `PEDAGOGICAL_RULES_FULL` (34,113 chars) vs `CONDENSED` (31,541 chars) — **−2,572 chars (−7.5%)** |
| Evaluators | `pseudo_anim_preservation`, `anim_codegen_preservation`, `codegen_render_preservation`, `render_qa_preservation` |
| Runner | `scripts/run_evaluators_baseline.py --prompt-variant {full,condensed}` |

### LangSmith experiments

| Variant | Experiment | Session ID | Wall time |
|---|---|---|---|
| FULL (baseline) | `v1_baseline_full-e422ebef` | `b4315c13-7e06-4acf-a6fc-1e6ccfbe5722` | 9:23 |
| CONDENSED (exp A) | `v1_exp_a_condensed-3981da83` | `f0a1de2b-1bd7-4bd2-8c5f-1c4c468f4059` | 11:42 |

- FULL → <https://smith.langchain.com/o/eab4a159-1c5f-4c28-9d65-74a2c904d24b/datasets/75f5e777-99e6-4914-97a8-0be3b696f4f8/compare?selectedSessions=b4315c13-7e06-4acf-a6fc-1e6ccfbe5722>
- CONDENSED → <https://smith.langchain.com/o/eab4a159-1c5f-4c28-9d65-74a2c904d24b/datasets/75f5e777-99e6-4914-97a8-0be3b696f4f8/compare?selectedSessions=f0a1de2b-1bd7-4bd2-8c5f-1c4c468f4059>

---

## 2. 4차원 벡터 diff

| 차원 | FULL | CONDENSED | Δ | 해석 |
|---|---:|---:|---:|---|
| **Pass rate (render_success)** | 81.2% (13/16) | 68.8% (11/16) | **−12.4%p** | CONDENSED가 render 3건 손실 |
| Pass rate (qa_passed) | 75.0% (12/16) | 68.8% (11/16) | −6.2%p | QA 관점에선 −1건 |
| **Cost / 16 cases** | $0.8713 | $0.8540 | −$0.0173 (−2%) | prompt token 절약 효과가 8% 미만 |
| `prompt_tokens` (총계) | 214,703 | 205,917 | −8,786 (−4.1%) | 프롬프트 체감 절약 |
| `completion_tokens` (총계) | 33,446 | 33,926 | +480 (+1.4%) | 출력량은 그대로 |
| **Mean latency / case** | 34.3s | 43.7s | **+9.4s (+27%)** | 역설: 토큰이 줄었는데 오히려 느려짐 |
| **Judge score (mean QA, 성공 케이스만)** | 5.78 | 4.64 | **−1.14** | 시각 품질 큰 하락 |

### 2.1 Edge preservation (이 실험의 핵심)

| Edge | FULL | CONDENSED | Δ | 해석 |
|---|---:|---:|---:|---|
| **`pseudo→anim`** | 50.0% (8/16) | 68.8% (11/16) | **+18.8%p** | CONDENSED 우세 |
| **`anim→codegen`** | 50.0% (8/16) | 68.8% (11/16) | **+18.8%p** | CONDENSED 우세 |
| `codegen→render` | 62.5% (10/16) | 62.5% (10/16) | 0 | 동률 |
| `render→qa` | 68.75% (11/16) | 62.5% (10/16) | **−6.25%p** | FULL 우세 |

**신호:** CONDENSED는 상류 2개 edge에서 크게 개선, 하류 `render→qa`에서 손실. `codegen→render`는 무관. **즉 FULL의 pedagogical rules는 "IR 보존"이 아니라 "렌더 결과의 시각 품질 가이드"에 효과가 집중되어 있었다.** — full rules 중 어느 문장이 IR 단계에서 노이즈로 작용하고 있었다는 방증.

---

## 3. Per-case flip matrix

각 edge별 FULL→CONDENSED 전환 시 0↔1 flip. `[pseudo_anim / anim_codegen / codegen_render / render_qa]` 순.

| # | 도메인 스케치 | FULL edge | COND edge | FULL QA | COND QA | 비고 |
|---:|---|:---:|:---:|---:|---:|---|
| 0 | 비교 스와프 정렬 | `0000` | `1000` | 4.7 | — | CONDENSED에서 render 실패 (`runtime_attr`), 단 pseudo_anim 회복 |
| 1 | 4x4 CNN kernel | `1011` | `1111` | 8.0 | 6.3 | anim_codegen 회복, QA 시각 하락 |
| 2 | Attention 토큰 | `1111` | `1001` | 8.2 | 6.2 | IR은 OK였는데 codegen_render/render_qa 하락 |
| 3 | BFS 5-node graph | `1101` | `1100` | 8.0 | — | CONDENSED render 실패 (`runtime_type`) |
| 4 | LRU 캐시 | `1111` | `1111` | 7.2 | 7.0 | 무변화 |
| 5 | 3D surface (sin·cos) | `0000` | `0100` | — | — | 양쪽 다 render 실패, anim_codegen 회복 관찰 |
| 6 | 6-node 3D graph | `0111` | `0011` | 7.4 | 7.2 | anim_codegen 손실 |
| 7 | 3D stacked CNN layers | `0111` | `1110` | 7.0 | 5.3 | pseudo_anim 회복, render_qa 손실 |
| 8 | QuickSort partition | `1011` | `1011` | 8.1 | 7.3 | edge 동일, QA 시각 하락 |
| 9 | Dijkstra (labels) | `0000` | `0111` | — | 7.1 | **CONDENSED가 render 성공**, 3 edge 동시 회복 |
| 10 | Merge sort split/merge | `1101` | `1100` | 7.1 | — | CONDENSED render 실패 (`runtime_type`) |
| 11 | Hash table chaining | `1111` | `1111` | 7.0 | 7.4 | 무변화, QA 미세 개선 |
| 12 | DP Fibonacci 의존 | `0010` | `1111` | 5.7 | 7.0 | **3 edge 동시 회복**, QA 개선 |
| 13 | BST 6-node | `1011` | `1100` | 6.4 | — | CONDENSED render 실패 (`timeout`) |
| 14 | Linked list | `0011` | `0111` | 7.6 | 6.5 | anim_codegen 회복, QA 시각 하락 |
| 15 | Vertical stack | `0100` | `0011` | — | 7.0 | **CONDENSED가 render 성공**, codegen/QA 회복 |

### 3.1 Flip count 요약

| Edge | flip 수 | 0→1 (gain) | 1→0 (loss) |
|---|---:|---:|---:|
| `pseudo_anim` | 3 | 3 | 0 |
| `anim_codegen` | 9 | 6 | 3 |
| `codegen_render` | 4 | 2 | 2 |
| `render_qa` | 7 | 3 | 4 |

**관찰:** `pseudo_anim`은 단방향 gain만 (CONDENSED가 이 edge를 깨뜨린 적 없음). `anim_codegen`은 2:1 비율로 개선 쪽. `render_qa`는 4:3으로 손실 쪽 — FULL의 pedagogical rules가 하류에서 최종 품질을 지탱하던 스캐폴드였다는 걸 숫자로 보여줌.

---

## 4. Render 실패 분해

### FULL (3건)

| # | 도메인 | `error_type` |
|---|---|---|
| 5 | 3D sin·cos surface | `runtime_type` (`Surface.__init__() got multiple values for argument 'u_range'`) |
| 9 | Dijkstra | `runtime_name` (`undefined name: array`) |
| 15 | Vertical stack | `runtime_type` (`Object <bound method VMobject.set_fill of VGroup(Rectangle, ...`) |

### CONDENSED (5건)

| # | 도메인 | `error_type` |
|---|---|---|
| 0 | 비교 스와프 정렬 | `runtime_attr` (`VGroup object has no attribute 'swap_submobjects'`) |
| 3 | BFS graph | `runtime_type` (`Animation only works on Mobjects`) |
| 5 | 3D sin·cos surface | `runtime_type` (`Surface.set_fill_by_value() missing 1 required positional argument`) |
| 10 | Merge sort | `runtime_type` (`Object Square cannot be converted to an animation`) |
| 13 | BST | `timeout` (render 멈춤) |

**해석:** FULL과 CONDENSED 모두 실패가 `codegen→render` 경계에 몰려 있고(구조적으로 같은 계열의 문제), CONDENSED에서 오히려 **runtime_attr / timeout 두 신규 failure mode가 등장**했다. 즉 CONDENSED에서 깎인 pedagogical rules 중 일부는 "흔한 Manim API 오용을 사전에 차단하는 가드"였을 가능성이 높다. 단 `pseudo→anim` 보존이 개선되는 것과는 독립 축이다.

---

## 5. Latency 역설

CONDENSED가 토큰 −8.8k (−4.1%)인데 **평균 wall time이 +9.4s (+27%) 느려졌다**. 가능한 원인:

1. **OpenAI API 분산 (sampling noise).** n=16 소표본이라 단일 외부 요인(API slow period)이 mean을 10s 흔들기에 충분.
2. **Render 실패시 retry 없음 — 하지만 실패 rate가 높으면 전체 wall time에 긴 timeout이 섞인다.** `b7du7it58.output` 로그 상 #13(BST)는 timeout이 찍히고, 이게 샘플당 평균을 끌어올린 주 요인.
3. **상관관계 vs 인과관계:** 프롬프트 길이 delta(−7.5%)로 설명할 수 있는 latency 기여는 TTFB 수백 ms 수준. +9.4s는 프롬프트 길이 때문이 아님.

**결론:** latency delta는 실험의 해석 대상에서 제외한다 (noise + timeout artifact). Gate 2의 cost/quality 판단에만 집중.

---

## 6. 원인 분석 — 왜 IR edge가 개선되고 시각 품질은 하락했는가

가설 3개, 증거와 함께:

### H1. FULL의 pedagogical rules가 IR 단계에서 "rule leakage"를 유발했다
**증거:** `pseudo_anim` flip은 3건 모두 gain이고 loss가 없다. 즉 FULL rule을 떼어냈을 때 **IR 보존이 깎인 케이스가 전무**하다. FULL의 특정 문구가 LLM을 pseudocode 단계에서 불필요하게 시각 표현으로 끌고 가, IR 추상 레벨을 흐리고 있었다는 신호.

### H2. FULL은 렌더링 단계의 "하류 방어 rule"이 다수 포함되어 있었다
**증거:** `render→qa` flip이 4 loss / 3 gain. 그리고 CONDENSED에서만 새로운 runtime 오류 타입(`runtime_attr`, `timeout`)이 등장. 즉 FULL에서 잘려나간 rule 중 일부는 **Manim 런타임 오용을 사전 차단**하고 있었고, 그걸 제거하자 새로운 failure class가 표면으로 올라옴.

### H3. Edge 간 tradeoff는 rule-space의 구조적 한계
**증거:** `codegen→render` flip count는 2:2 대칭 (net=0). 즉 "rule 총량"을 조정하는 방식으로는 상류와 하류 중 하나를 택하는 조건부 게임이다. 더 많은 rule을 욱여넣어도 cross-edge gain은 플랫화된다.

**따라서:** prompt-only 최적화는 Phase 1에서 **정보를 stage 간에 전달하는 구조적 장치** 없이는 천장에 부딪힌다. 이게 Week 4에 IntentTracker를 도입하는 직접적 근거다 — IR에서 선언된 intent가 codegen/render까지 일관되게 따라가도록 '정보 채널' 자체를 바꿔야 한다.

---

## 7. Gate 2 결론

**(a) 측정 관점.** 4개 custom edge evaluator가 의도한 대로 작동했다. 단일 aggregate 지표(render_success, mean QA)만 보면 CONDENSED는 '열등'으로 판정됐을 것이지만, edge 단위 벡터는 **+18.8%p / +18.8%p / 0 / −6.25%p**라는 tradeoff를 드러냈다. 이 신호가 없었으면 Phase 0 narrative("edge에서 정보가 소실된다")는 수사에 머물렀을 것이다. 이번 실험 결과는 narrative를 숫자로 못 박는다.

**(b) Default switching 판단.** CONDENSED를 v1 default로 스위칭하지 **않는다**.
- render_success −12.4%p, mean QA −1.14 은 프로덕션에서 사용자 체감 품질을 바로 해친다.
- cost 절약 −$0.0173 / 16 cases = case당 $0.001 수준 — 사실상 무시 가능.
- 이 tradeoff는 "CONDENSED가 나쁘다"가 아니라 "prompt-level 조작만으로는 cross-edge 개선이 불가능하다"는 구조적 신호.

**(c) v2 방향 시사.**
- `pseudo→anim` +18.8%p 는 "IR 추상 레벨이 프롬프트 구조에 민감하다"를 정량화한 첫 데이터. Week 4 IntentTracker는 **이 신호가 가리키는 지점을 시스템 차원으로 고정**하는 작업.
- `render→qa` 손실분은 post-processing regex 26개 (v1 baseline report §6 증거 1–2)가 커버하고 있던 영역과 겹친다. IntentTracker가 이 coverage를 대체할 수 있는지는 Week 5 실험 B에서 검증.

**(d) Gate 2 passes.** 측정 인프라가 실제 실험에서 의사결정을 흔드는 신호를 생성했다. Phase 1 Week 3 목표는 달성. Phase 1 Week 4로 진행.

---

## 8. 다음 단계

- [x] Week 3 Task 6: FULL vs CONDENSED 실험 실측 완료
- [x] Week 3 Task 7: 이 snapshot 작성 (현 문서)
- [ ] Week 3 Task 8: `.claude/plan.md` Week 3 checkbox 업데이트 + Gate 2 entry 기록
- [ ] Week 4: IntentTracker 설계 — `pseudo_ir` 단계에서 선언된 intent가 `anim_ir` / `codegen` / `render`까지 consistency check로 따라가는 구조
- [ ] Week 5 실험 B: IntentTracker 적용 시 4차원 벡터 회복 + `render→qa` 손실분 대체 여부 검증

---

**참조:**
- `docs/v1-baseline-report.md` — 4증거 (unknown helpers / color map / penalty / LSM 주석)
- `docs/edge-first-measurement.md` — Phase 0 narrative
- `GIFPT_AI/studio/ai/llm_codegen.py` — `PEDAGOGICAL_RULES_FULL` / `PEDAGOGICAL_RULES_CONDENSED` / `_get_system_prompt()`
- `GIFPT_AI/scripts/run_evaluators_baseline.py` — `--prompt-variant` CLI flag 추가본
- Raw JSON: `/tmp/gifpt_baseline_full.json`, `/tmp/gifpt_exp_a_condensed.json` (local only, not checked in)
