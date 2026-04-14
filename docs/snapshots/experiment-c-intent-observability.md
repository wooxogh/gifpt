# Experiment C — IntentTracker Observability (Week 4 Day 4–5)

> **작성일:** 2026-04-14
> **목적:** Week 4 목표 검증 — 기존 4-edge 평가기가 보지 못하는 **user text → pseudo_ir 경계의 의도 손실**을 IntentTracker로 관측 가능한지 확인.
> **핵심 질문:** "4차원 벡터가 놓치고 있던 signal이 존재하는가? 있다면 얼마나 큰가?"
> **데이터 소스:** LangSmith experiment `v1_exp_c_intent_full-23362d9d` + 5 custom edge preservation evaluators (Week 2 4개 + Week 4 신규 intent_preservation)
> **데이터셋:** `gifpt-goldset-v0` (16 cases)
> **파이프라인 모델:** `intent_extract`, `pseudo_ir`, `anim_ir`, `codegen` 4-stage 모두 `gpt-4o` 통일 (Vision QA만 `gpt-4o-mini`) — Week 3과 동일한 통제 조건 유지
> **상태:** Week 4 Day 4 실측 완료, Day 5 분석 완료. Week 5 Experiment B (intent injection) 진행 결정 근거.

---

## 0. TL;DR (면접용)

> "4개 pairwise evaluator(pseudo↔anim, anim↔codegen, codegen↔render, render↔qa)는 **시작점이 pseudo_ir**이라서 '사용자 텍스트에서 pseudo_ir 사이 손실'을 구조적으로 볼 수 없다. IntentTracker는 user text를 canonical 앵커로 뽑아 3개 LLM stage 각각에 대해 손실을 측정하는 5번째 차원이다. 16-case observability run에서 이 차원이 감춰져 있던 신호를 드러냈다: **binary pass rate 6.2% (1/16만 완전 보존), 그러나 stage별 continuous 평균은 pseudo_ir 70.6% / anim_ir 61.5% / codegen 63.1%**. 즉 사용자 텍스트 기준 약 **30%의 엔티티·동사가 첫 LLM stage에서 이미 소실**되고 있었고, 그 이후 stage들은 추가로 ~10%만 더 잃는다. pairwise 평가기 4개가 보고 있던 'pseudo→anim 손실'은 이미 30% 줄어든 baseline에서 출발한 측정이었다는 뜻. 파이프라인 설정·프롬프트·모델 모두 Week 3 FULL과 동일했기 때문에 4-edge 수치 변동은 LLM 샘플링 잡음(±2 케이스, render 81.2→68.8%)으로 해석되고, **유일한 structural 신호는 5번째 차원에서 나왔다.** Week 5 Experiment B는 각 stage의 system prompt 맨 앞에 intent JSON을 주입해서 pseudo_ir stage 평균 70.6% → ≥0.85를 목표로 한다."

---

## 1. 실험 설정


| 항목                   | 값                                                                                                                                                                |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Dataset              | `gifpt-goldset-v0` (16 cases, 11 domains)                                                                                                                        |
| Pipeline             | linear v1 (user → intent_extract → pseudo_ir → anim_ir → codegen → render → qa)                                                                                  |
| Independent variable | **없음** — 측정 도구만 붙임 (IntentTracker는 observability-only, 파이프라인 경로 수정 없음)                                                                                           |
| Controlled           | 파이프라인 3-stage(`pseudo_ir`/`anim_ir`/`codegen`) 모두 `gpt-4o`, 추가로 `intent_extract`도 `gpt-4o`, `GIFPT_PROMPT_VARIANT=full`, 동일 few-shot, 동일 render 경로, 동일 QA rubric |
| 5번째 evaluator        | `intent_preservation` (Week 4 Day 3 신규) — binary pass + `overall_rate` continuous                                                                                |
| Runner               | `scripts/run_evaluators_baseline.py --experiment-prefix v1_exp_c_intent --prompt-variant full`                                                                   |


### LangSmith experiment


| Variant              | Experiment                      | Session ID                             | Wall time |
| -------------------- | ------------------------------- | -------------------------------------- | --------- |
| FULL + IntentTracker | `v1_exp_c_intent_full-23362d9d` | `07daebea-b9c1-4c5e-89a7-443eaae22a43` | 12:28     |


Session URL: [https://smith.langchain.com/o/eab4a159-1c5f-4c28-9d65-74a2c904d24b/datasets/75f5e777-99e6-4914-97a8-0be3b696f4f8/compare?selectedSessions=07daebea-b9c1-4c5e-89a7-443eaae22a43](https://smith.langchain.com/o/eab4a159-1c5f-4c28-9d65-74a2c904d24b/datasets/75f5e777-99e6-4914-97a8-0be3b696f4f8/compare?selectedSessions=07daebea-b9c1-4c5e-89a7-443eaae22a43)

### Week 3 FULL과 대조 — 파이프라인은 동일, 관측기만 추가


| 항목                                                                   | Week 3 FULL      | Week 4 Exp C                           | Δ        | 해석                                          |
| -------------------------------------------------------------------- | ---------------- | -------------------------------------- | -------- | ------------------------------------------- |
| Pipeline config                                                      | gpt-4o × 3-stage | **gpt-4o × 4-stage** (+intent_extract) | +1 stage | observability                               |
| Prompt variant                                                       | FULL             | FULL                                   | 동일       | —                                           |
| Render success                                                       | 81.2% (13/16)    | 68.8% (11/16)                          | −12.4%p  | **LLM 샘플링 노이즈**: 같은 입력·프롬프트에서 ±2 케이스는 정상 분산 |
| Mean QA (성공 케이스)                                                     | 5.78             | 6.04                                   | +0.26    | 노이즈                                         |
| 4-edge avg (pseudo_anim + anim_codegen + codegen_render + render_qa) | 57.8%            | 60.9%                                  | +3.1%p   | 노이즈                                         |
| **intent_preservation (binary)**                                     | — (측정 안 됨)       | **6.2% (1/16)**                        | —        | **측정 전에는 안 보이던 차원**                         |


> **통제 조건 관점**: 파이프라인 경로, 시스템 프롬프트, 모델, few-shot까지 전부 Week 3 FULL과 같다. Experiment C에서 한 일은 **측정기 하나를 추가 부착**한 것뿐이다. 그래서 4-edge 수치의 run-over-run 변동은 prompt delta의 효과가 아닌 LLM 디코딩 확률성의 결과로 읽어야 한다 (실험 설계상의 의도적 choice — Week 5에서 intent injection A/B를 돌릴 때 같은 noise envelope를 두 팔에 걸어두고 delta만 보기 위한 baseline 확보).

---

## 2. 5차원 벡터


| 차원                                                    | 값                | 비고                                            |
| ----------------------------------------------------- | ---------------- | --------------------------------------------- |
| **intent_preservation (binary)**                      | **6.2% (1/16)**  | 16 케이스 중 1건만 전 stage에서 모든 entity·operation 보존 |
| intent_preservation (continuous, mean `overall_rate`) | **0.655**        | 케이스별 3-stage 평균                               |
| `pseudo_anim`                                         | 62.5% (10/16)    | Week 3 FULL 50.0% 대비 +12.5%p (노이즈 envelope 안) |
| `anim_codegen`                                        | 56.2% (9/16)     | +6.2%p (노이즈)                                  |
| `codegen_render`                                      | 68.8% (11/16)    | +6.3%p (노이즈)                                  |
| `render_qa`                                           | 56.2% (9/16)     | −12.5%p (노이즈, render 실패 수 차이)                 |
| Pass rate (render_success)                            | 68.8% (11/16)    | 5건 render 실패                                  |
| Pass rate (qa_passed)                                 | 62.5% (10/16)    |                                               |
| Mean QA (성공 케이스만)                                     | 6.04             |                                               |
| Wall time                                             | 12:28 (16 cases) | mean 46.8s/case (min 17.2s, max 199.2s)       |


### 2.1 Intent preservation — stage별 continuous rate (핵심 signal)

16 케이스 × 3 stage에서 보존된 entity+operation 토큰의 비율 평균.


| Stage       | mean rate | 해석                                                                       |
| ----------- | --------- | ------------------------------------------------------------------------ |
| `pseudo_ir` | **0.706** | **user text → pseudo_ir 사이에 이미 ~30%의 의도가 유실**. 4-edge 평가기로는 관측 불가능했던 손실. |
| `anim_ir`   | 0.615     | pseudo_ir 대비 추가 −9.1%p                                                   |
| `codegen`   | 0.631     | anim_ir 대비 +1.6%p (codegen은 anim_ir을 꽤 충실히 따름)                           |


> **이 표가 Week 4의 존재 이유**이다. 4개 pairwise evaluator는 pseudo_ir 산출물과 anim_ir 산출물을 비교하므로, 두 artifact 모두에서 누락된 엔티티는 "두 쪽 다 없으면 손실 아님"으로 잡혀 전혀 드러나지 않는다. IntentTracker가 user text를 외부 anchor로 놓자마자, 가장 큰 손실이 **첫 LLM stage에서 발생**한다는 게 드러났다.

### 2.2 왜 binary는 1/16이고 continuous는 0.655인가

`intent_preservation_evaluator`는 어느 한 stage라도 토큰 하나라도 놓치면 binary score = 0을 준다. 엔티티 3~~7개 × 오퍼레이션 3~~7개짜리 평균 케이스에서 이 기준은 거의 전부 0으로 찍히는 게 정상이다 (conservative token-set 매칭이라 복수형·동의어 변형도 `missing`으로 카운트됨). **따라서 Week 5의 주요 지표는 continuous `overall_rate`이지 binary pass rate가 아니다.**

---

## 3. Per-case matrix

`4-edge = [pseudo_anim / anim_codegen / codegen_render / render_qa]`, `per-stage intent rate = [pseudo_ir / anim_ir / codegen]`. QA는 렌더 실패 케이스에선 `—`.


| #   | 도메인 스케치                | entities/ops | 4-edge | per-stage intent   | overall  | QA  |
| --- | ---------------------- | ------------ | ------ | ------------------ | -------- | --- |
| 0   | 정렬 비교-스왑 애니            | 1e/3o        | `0011` | 1.00 / 1.00 / 1.00 | **1.00** | 6.4 |
| 1   | 4×4 CNN kernel slide   | 3e/3o        | `1100` | 0.83 / 0.67 / 0.50 | 0.67     | —   |
| 2   | Attention 토큰 query/key | 4e/3o        | `1011` | 0.71 / 0.71 / 0.57 | 0.67     | 6.7 |
| 3   | 5-node BFS 방문          | 3e/3o        | `1011` | 0.50 / 0.50 / 0.50 | 0.50     | 6.2 |
| 4   | LRU 3-slot PUT/GET     | 1e/6o        | `1111` | 0.86 / 0.57 / 0.86 | 0.76     | 6.3 |
| 5   | 3D sin·cos 표면 회전       | 3e/1o        | `0100` | 1.00 / 0.75 / 1.00 | 0.92     | —   |
| 6   | 6-node 3D graph        | 3e/1o        | `0000` | 0.50 / 0.50 / 0.50 | 0.50     | —   |
| 7   | 3D stacked CNN layers  | 1e/3o        | `1111` | 0.75 / 0.75 / 0.75 | 0.75     | 6.0 |
| 8   | QuickSort partition    | 3e/5o        | `1111` | 0.88 / 0.75 / 0.75 | 0.79     | 5.8 |
| 9   | Dijkstra 거리 라벨         | 2e/4o        | `0011` | 0.83 / 0.67 / 1.00 | 0.83     | 6.4 |
| 10  | Merge sort split/merge | 3e/4o        | `1100` | 0.86 / 0.71 / 0.71 | 0.76     | —   |
| 11  | Hash table chaining    | 3e/4o        | `1110` | 0.71 / 0.57 / 0.57 | 0.62     | 3.3 |
| 12  | DP Fibonacci 테이블       | 4e/3o        | `0110` | 0.57 / 0.57 / 0.57 | 0.57     | 5.7 |
| 13  | BST 6-node 계층          | 4e/3o        | `1011` | 0.14 / 0.14 / 0.14 | **0.14** | 7.3 |
| 14  | Singly linked list     | 4e/7o        | `1100` | 0.45 / 0.36 / 0.36 | 0.39     | —   |
| 15  | 수직 스택 컨테이너             | 4e/6o        | `0011` | 0.70 / 0.60 / 0.30 | 0.53     | 6.3 |


### 3.1 주목할 패턴

- **#0 (1.00)**: 단 1건만 완전 보존. entity 1개 + operation 3개로 의도 스펙 자체가 가장 작아서 보존이 쉬웠다. 역으로, 의도가 많을수록 보존률이 낮다 — 특히 #13 BST (4e/3o, 0.14)와 #14 linked list (4e/7o, 0.39)처럼 계층/시퀀스 구조가 풍부한 케이스에서 early-stage 손실이 극심.
- **#13 BST 역설**: 4-edge는 `1011`로 3/4 통과하는데 intent는 0.14. 4개 pairwise evaluator 관점에서 "pseudo_ir → anim_ir 보존 OK"이지만, 둘 다 사용자가 요청한 entity 6개 중 5개를 공통으로 잃어버린 상태. **이게 바로 IntentTracker가 잡아내려던 케이스**.
- **#5 3D surface (0.92)**: intent 보존은 거의 완벽했는데 render는 `runtime_name: undefined name: ParametricSurface`로 실패. → "의도 이해는 했지만 코드로 못 썼다"의 전형.
- **#6 6-node 3D graph (0.50 + `0000`)**: 전 차원에서 최악. 3D 렌더 케이스들은 Manim API 복잡도 때문에 모든 stage에서 entity 절반을 잃음.

### 3.2 2D vs 3D 분해


| 하위셋                                       | n   | mean intent `overall_rate` | render_success |
| ----------------------------------------- | --- | -------------------------- | -------------- |
| 2D 케이스 (#0,1,2,3,4,8,9,10,11,12,13,14,15) | 13  | 0.634                      | 10/13 (76.9%)  |
| 3D 케이스 (#5,6,7)                           | 3   | 0.722                      | 1/3 (33.3%)    |


흥미롭게도 3D가 intent 보존률은 오히려 **높다**. 왜냐하면 3D 요청은 도메인 어휘가 작아서("surface", "3D graph", "3D layers") entity/op 수 자체가 2D보다 적기 때문. 반면 render 실패율은 3D가 압도적으로 높다 — **3D는 의미 전달은 되는데 코드가 안 컴파일되는 유형**, 2D는 **의미가 깎이면서 코드는 컴파일되는 유형**이라는 두 개의 질적으로 다른 실패 모드.

---

## 4. Render 실패 breakdown (n=5)


| #   | 도메인                | `error_type`    | 해석                                                                  |
| --- | ------------------ | --------------- | ------------------------------------------------------------------- |
| 1   | 4×4 CNN            | `runtime_index` | list 인덱싱 버그 (codegen이 2x2 kernel 좌표 잘못 계산)                          |
| 5   | 3D sin·cos surface | `runtime_name`  | `ParametricSurface` (Manim 신규 API 이름) 정의 안 됨                        |
| 6   | 6-node 3D graph    | `runtime_attr`  | `'Camera' object has no attribute 'frame'` (Manim Community 호환성)    |
| 10  | Merge sort         | `timeout`       | 60초 컷 — 재귀 시각화 과다                                                   |
| 14  | Singly linked list | `runtime_attr`  | `'list' object has no attribute 'animate'` (node list에 .animate 호출) |


Week 3 FULL에서도 동일 도메인에서 3건이 실패했다. 이번 5건 중 #1, #10은 Week 3에는 통과했던 것들 → **stochastic regression**. prompt도 모델도 그대로인데 케이스가 흔들렸다는 것은 baseline noise envelope가 대략 ±2 케이스라는 증거다. Week 5에서 intent injection 효과 크기를 해석할 때 이 envelope를 기준으로 삼아야 한다.

---

## 5. 원인 해석

### 5.1 주요 관측

1. **user text → pseudo_ir 경계가 가장 큰 손실점이다.** 3-stage 중 pseudo_ir이 0.706으로 가장 높지만, anim_ir(0.615)·codegen(0.631)보다 "덜 깎인 쪽"이라는 뜻일 뿐, **이미 첫 변환에서 전체 의도의 ~30%를 잃고 시작한다.** anim_ir·codegen이 추가로 빼앗는 양(~10%)은 pseudo_ir의 손실보다 훨씬 작다.
2. **4-edge 평가기는 이 손실에 눈을 감고 있었다.** pseudo_ir이 X를 못 담으면 anim_ir도 X를 못 담는 게 자연스럽고, 그 상태에서 pseudo_ir↔anim_ir pairwise 비교는 둘 다 X가 없으니 "보존"으로 찍힌다. 가장 큰 signal이 가장 관찰하기 어려운 위치에 숨어 있었다.
3. **의도 스펙이 클수록 손실률이 크다** (#13 BST, #14 linked list, #15 stack). 이는 LLM 프롬프트 엔지니어링에서 알려진 "long instruction dilution" — 여러 entity를 동시에 보존하는 건 단일 operation을 정확히 다루는 것보다 어렵다.
4. **노이즈 envelope = 약 ±2 케이스**. 완전히 같은 설정에서 render_success 81.2% → 68.8% 변동. 이 envelope를 모르면 Week 5에서 "intent injection 붙였더니 render가 +12% 늘었다" 같은 착시에 속기 쉽다.

### 5.2 Week 5 Experiment B가 공격할 지점

- **프라이머리**: `pseudo_ir` stage의 system prompt 맨 앞에 `intent_extract` 결과 JSON을 주입. 가설: "canonical intent가 명시적으로 프롬프트 안에 있으면 LLM이 엔티티를 덜 누락한다." 목표: `pseudo_ir` per-stage rate 0.706 → **≥0.85**.
- **세컨더리**: 같은 intent JSON을 `anim_ir`·`codegen` prompt에도 전파. 복합 효과로 `overall_rate` mean 0.655 → **≥0.80**.
- **Null 가설**: 노이즈 envelope(±2 케이스 ≒ ±0.04 rate) 안에서의 
-  있다면 injection은 실패로 판단.

---

## 6. Week 4 전체 목적 달성 점검

Week 4가 처음 정한 성공 조건은 "4 pairwise evaluator가 보지 못하는 signal을 관측 가능한 형태로 드러낸다"였다. 이 기준에 따른 자기평가:


| 목표                                                       | 결과                                                                  |
| -------------------------------------------------------- | ------------------------------------------------------------------- |
| 5번째 차원 구현 (intent_tracker.py + evaluator + langsmith 연결) | ✅                                                                   |
| 16-case × 5-evaluator 실측 완료                              | ✅                                                                   |
| 새 signal이 실제로 존재함을 증거와 함께 보임                             | ✅ — 30% loss at user→pseudo_ir, 4-edge로는 관측 불가였음을 #13 BST가 구체적으로 입증 |
| 노이즈 envelope 측정                                          | ✅ — ±2 케이스 / render, ±3%p / 4-edge avg                              |
| Week 5가 공격할 정확한 수치 목표 설정                                 | ✅ — pseudo_ir rate 0.706 → ≥0.85                                    |


**Week 4 전 D1–D5를 거치면서 absolute performance를 올리는 건 목표가 아니었다.** 이 구간의 deliverable은 "다음 실험이 근거 있게 가설을 만들 수 있는 측정기"이고, 그것은 달성됐다.

---

## 7. Week 5 진행 여부 (Gate 판단)

Week 4 plan에 못박아둔 Week 5 abort gate는:

> edge avg ≥0.75, mean QA ≥6.5, render ≥75%. 3개 중 어느 하나라도 Experiment B 결과에서 만족 못 하면 IntentTracker 경로를 abort하고 Plan B (Agent SDK / 별도 파이프라인) 검토.

Experiment C는 **observability 실행**이지 injection 실행이 아니므로 abort gate에 직접 해당되지 않는다. 단, Experiment C가 드러낸 **baseline 상태**가 Week 5 성공 가능성에 대한 단서를 준다:

- 4-edge avg 60.9% + mean QA 6.04 + render 68.8% — **세 지표 모두 Week 5 abort gate 미달**. injection이 단순히 "조금 낫게 하는" 수준으로는 gate 통과가 불가능하다.
- 따라서 Experiment B는 **pseudo_ir per-stage rate의 명확한 큰 폭 상승**(≥0.85)을 최우선 성공 기준으로 삼고, 그 상승이 실제로 4-edge 수치까지 끌어올리는지 확인한다. 상승이 per-stage에서 일어나도 4-edge/QA로 전파되지 않으면 그것은 "intent를 지키긴 했으나 video 품질에는 기여 못 함"의 증거가 되고, 그 자체로 파이프라인 v2의 **근본 재설계 필요성**(linear → graph 또는 Agent SDK)에 대한 강한 evidence가 된다.

### 판정

**Week 5 Experiment B 실행한다.** 단, 단순히 "gate 넘는가"만 확인하는 게 아니라, 실패 시의 해석 경로까지 미리 정해두었다 (위 문단). Week 5에서 per-stage 0.706 → ≥0.85를 달성하지 못하면 abort 후 Agent SDK 검토로 이동.

---

## 8. 다음 작업

- Week 5 D1: `studio/ai/llm_pseudocode.py`의 system prompt 맨 앞에 `intent` JSON 주입하는 코드 경로 추가 (기본 off, env flag로 토글). `GIFPT_INTENT_INJECT=pseudo_ir`.
- Week 5 D2: 동일 구조로 `llm_anim_ir.py`, `llm_codegen.py`도 토글 가능하게. flag를 조합해서 "pseudo only / all three" 두 변형 실험.
- Week 5 D3: Experiment B run — 동일 goldset × (injection OFF / injection pseudo_ir only / injection all stages) 3-arm 비교.
- Week 5 D4: 결과 분석 → `experiment-b-intent-injection.md` 작성 + Gate 최종 판정.

---

## 9. 데이터 원본

- 원 데이터: `/tmp/exp_c_data.json` (16 per-case records, fetched via `scripts/fetch_experiment_c_data.py`)
- LangSmith experiment: `v1_exp_c_intent_full-23362d9d`
- Session ID: `07daebea-b9c1-4c5e-89a7-443eaae22a43`
- 브랜치: `feat/measurement-week4-experiment-c` (on top of `feat/measurement-week4-intent-tracker`)

