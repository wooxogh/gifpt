# GIFPT v1 Failure Taxonomy — Edge-First Reclassification

> **작성일:** 2026-04-12
> **목적:** 기존 6-stage taxonomy(`scripts/failure_audit.py` STAGE_PATTERNS)를 **edge 원인**으로 재분류. Phase 0 산출물.
> **데이터 소스:** `GIFPT_AI/reports/failure_audit_2026-04-09.md` (최근 7일, 11 jobs, 8 failures)

---

## 1. 왜 edge-first 재분류인가

기존 `failure_audit.py`의 6-stage taxonomy는 "어느 단계에서 에러가 났는가"를 본다. 하지만 GIFPT의 실제 실패는 대부분 **단계 사이의 핸드오프에서 정보가 소실**될 때 발생한다:

- `dijkstra`가 codegen 단계에서 `NameError: Graph not defined`로 죽는다 → codegen의 버그가 아니라, anim_ir가 "graph 엔티티"를 표현했는데 codegen이 이를 Manim의 어떤 객체로 번역해야 할지 **몰랐기** 때문.
- `cnn_convolution`이 `unknown_helper`로 fail한다 → codegen이 hallucinate한 게 아니라, anim_ir가 "convolution operation"을 scene descriptor로 명시하지 않아서 codegen이 **상상력으로 helper를 지어낸** 결과.

따라서 "stage × 원인 edge" 두 축으로 재분류하면 실제 고쳐야 할 지점이 드러난다.

## 2. Stage → Edge 매핑

GIFPT v1 파이프라인: `user_request → pseudo_ir → anim_ir → manim_code → render → qa`

즉 4개의 handoff edge가 존재:

| Edge 이름 | From | To | 주된 실패 원인 |
|---|---|---|---|
| **`pseudo→anim`** | Pseudocode IR | Animation IR | 의도/엔티티/operation 소실, 도메인 분류 오류 |
| **`anim→codegen`** | Animation IR | Manim Code | Scene descriptor 누락 → helper hallucination, 색상/폰트 몰라서 invalid 참조 |
| **`codegen→render`** | Manim Code | 렌더 산출물 | Manim API 오용 (NameError, AttributeError), timeout |
| **`render→qa`** | 렌더 산출물 | QA verdict | 도메인별 required check 누락 (comparison_shown, elements_visible 등) |

기존 6-stage를 이 4 edge에 다음과 같이 매핑한다:

| 기존 stage (`STAGE_PATTERNS`) | 주 edge | 보조 edge |
|---|---|---|
| `ir_validation` | `pseudo→anim` | — |
| `codegen` (static check) | `anim→codegen` | — |
| `render` / `render_timeout` | `codegen→render` | `anim→codegen` (helper 헛것) |
| `qa` (vision score) | `render→qa` | `anim→codegen` (도메인 요구 누락) |
| `callback` | 인프라 (edge 아님) | — |
| `unknown` | 미분류 (taxonomy gap) | — |

## 3. 최근 실패 8건 edge 라벨링

`failure_audit_2026-04-09.md` 기준 — 8건 중 6건이 **edge에서 발생**했다 (callback + unknown 제외).

| # | Slug | Domain | 기존 stage | Edge 원인 | 증거 |
|---|---|---|---|---|---|
| 1 | `dijkstra` | graph_traversal | render | `codegen→render` | `NameError: Graph not defined` — Manim에 `Graph` 클래스 존재하는데 import 안 함 또는 잘못 참조 |
| 2 | `dijkstra` | graph_traversal | render_timeout | `codegen→render` | 180s timeout — 무한 루프 또는 과도한 애니메이션 |
| 3 | `dijkstra` | graph_traversal | render | `codegen→render` | `AttributeError: NoneType.shift` — 객체 생성 실패 후 메서드 호출 |
| 4 | `bfs` | graph_traversal | qa | `render→qa` | score 3.2 / 5.0 — graph_traversal 도메인 required check 미달 (`nodes_visible`, `edges_drawn`, `traversal_order`, `frontier_shown`) |
| 5 | `self_attention` | transformer | ir_validation | `pseudo→anim` | `validate_pseudocode_ir` 4 issues — 트랜스포머 attention 연산의 의도 추출 실패 |
| 6 | `cnn_convolution` | cnn_param | codegen | `anim→codegen` | `unknown_helper` — `_UNKNOWN_HELPERS` 리스트에 있는 hallucination 함수 호출 검출 |
| 7 | `lru_cache` | cache | callback | 인프라 | HTTP 503 Spring callback failed — edge 아님 |
| 8 | `weird_thing` | other | unknown | 미분류 | "something completely unexpected" — taxonomy gap, 재분류 필요 |

**Edge 분포:**
- `codegen→render`: 3건 (37.5%) ← 최빈
- `render→qa`: 1건 (12.5%)
- `pseudo→anim`: 1건 (12.5%)
- `anim→codegen`: 1건 (12.5%)
- 인프라: 1건 (12.5%)
- 미분류: 1건 (12.5%)

**관찰:** `graph_traversal` 도메인은 3개 서로 다른 edge (codegen→render 3건 + render→qa 1건)에서 실패한다. 이는 단일 stage의 버그가 아니라 **anim_ir 단계에서 graph 엔티티의 scene descriptor가 부실**하기 때문에 하류 edge들이 연쇄 실패하는 패턴으로 해석 가능하다. (= attribution graph의 root cause)

## 4. 도메인 × Edge 교차표

| Domain | `pseudo→anim` | `anim→codegen` | `codegen→render` | `render→qa` | Total |
|---|---:|---:|---:|---:|---:|
| graph_traversal | 0 | 0 | 3 | 1 | 4 |
| transformer | 1 | 0 | 0 | 0 | 1 |
| cnn_param | 0 | 1 | 0 | 0 | 1 |
| cache | (인프라) | | | | 1 |
| other | (미분류) | | | | 1 |
| sorting | 0 | 0 | 0 | 0 | 0 (전부 성공) |

**해석:** `graph_traversal`은 anim_ir의 "graph" 엔티티 표현력이 약해서 모든 하류 edge로 실패가 전파된다. `sorting`은 파이프라인이 충분히 성숙해서 0% 실패율 — 이건 편향된 few-shot 예제(`bubble_sort`, `quicksort_partition`, `merge_sort` 3개) 덕분일 가능성 높음 (커버리지 편향).

## 5. Taxonomy Gap — `unknown` 버킷

`failure_audit.py`의 `STAGE_PATTERNS`는 regex 매칭. `weird_thing`의 메시지처럼 새로운 에러 형태가 나오면 `unknown`으로 떨어진다. 이 버킷이 **매주 증가하는지** 모니터링해야 하며, 3건 이상 누적되면 STAGE_PATTERNS에 regex 추가.

## 6. 다음 단계

- [ ] `v1-baseline-report.md`에서 위 edge 분포를 4차원 벡터(pass rate/cost/latency/judge)와 함께 합본
- [ ] `edge-first-measurement.md`에서 "왜 stage가 아닌 edge인가"를 axiom으로 정리
- [ ] Phase 1 Week 2에서 4 edge 각각에 대응하는 LangSmith custom code evaluator 설계

---

**참조:**
- `GIFPT_AI/studio/ai/llm_codegen.py:427-433` — `_UNKNOWN_HELPERS` 리스트
- `GIFPT_AI/studio/ai/qa.py:275-295` — `DOMAIN_QA_CONFIG` (required checks)
- `GIFPT_AI/studio/video_render.py:312` — LSM-Tree 오분류 주석
- `GIFPT_AI/scripts/failure_audit.py:33-44` — `STAGE_PATTERNS`
