# GIFPT v1 Baseline Report

> **작성일:** 2026-04-12
> **목적:** v2 refactor의 비교 기준선 확보. 4차원 벡터(pass / cost / latency / judge)로 v1 상태를 수치화.
> **데이터 소스:** `GIFPT_AI/reports/failure_audit_2026-04-09.md` + `seed_audit_2026-04-09.md` + 코드 베이스 현장 증거
> **상태:** Week 1 초안. Week 3 실험 A 실행 시 LangSmith run으로 4차원 벡터 정식 수집 예정.

---

## 0. TL;DR (면접용)

> "v1 GIFPT는 최근 7일 동안 11개 요청 중 **72.7%가 실패**했다. 실패의 **75%가 4개 handoff edge에서** 발생했고, 나머지는 인프라/미분류였다. 내가 코드 베이스에서 수동으로 찾은 **4가지 정량 증거**는 — post-processing regex 26개, unknown_helper 리스트 11개, sorting 도메인 2.5점 페널티, LSM-Tree 오분류 자체 방지 주석 — 모두 **edge에서 정보가 소실될 때 v1이 어떻게 방어하려 했는지**를 보여준다."

## 1. 정량 요약

| 지표 | 값 | 소스 |
|---|---|---|
| 관찰 기간 | 2026-04-03 ~ 2026-04-09 (7일) | `failure_audit_2026-04-09.md` |
| 총 요청 수 | 11 | 동상 |
| 성공 | 3 (27.3%) | 동상 |
| 실패 | 8 (72.7%) | 동상 |
| Edge 원인 실패 | 6/8 (75%) | `failure-taxonomy.md` 재분류 |
| 인프라/미분류 | 2/8 (25%) | callback 1 + unknown 1 |
| Seed examples 수 | 16 | `seed_examples.jsonl` |
| 도메인 수 | 11 | (sorting/graph/cnn/transformer/cache/hash_table/dp/tree/linked_list/stack/math) |
| Domain QA required checks | 21 checks × 4 domains | `qa.py:275-340` |

## 2. Stage 분포 (기존 taxonomy)

| Stage | Count | % |
|---|---:|---:|
| Render | 2 | 25% |
| Render (timeout) | 1 | 12% |
| Vision QA | 1 | 12% |
| IR validation | 1 | 12% |
| Codegen | 1 | 12% |
| Callback | 1 | 12% |
| Unknown | 1 | 12% |
| **Total** | **8** | **100%** |

## 3. Edge 분포 (재분류)

| Edge | Count | % | 예시 failure |
|---|---:|---:|---|
| `codegen→render` | 3 | 37.5% | `dijkstra` × 3 (NameError, timeout, NoneType) |
| `render→qa` | 1 | 12.5% | `bfs` QA 3.2/5.0 |
| `pseudo→anim` | 1 | 12.5% | `self_attention` 4 IR issues |
| `anim→codegen` | 1 | 12.5% | `cnn_convolution` unknown_helper |
| 인프라 | 1 | 12.5% | `lru_cache` HTTP 503 |
| 미분류 | 1 | 12.5% | `weird_thing` |

## 4. 도메인 분포

| Domain | Total | Failed | Fail rate | 비고 |
|---|---:|---:|---:|---|
| graph_traversal | 4 | 4 | **100%** | 모든 edge로 분산 실패 |
| transformer | 1 | 1 | 100% | `pseudo→anim` edge |
| cnn_param | 1 | 1 | 100% | `anim→codegen` edge |
| cache | 1 | 1 | 100% | 인프라 |
| other | 1 | 1 | 100% | 미분류 |
| sorting | 3 | 0 | 0% | few-shot 편향 (3개 seed 모두 sorting) |

## 5. 4차원 벡터 (v1 baseline)

> **주의:** 이 4차원 벡터는 Week 1 현재 **pass rate만 실측**이다. cost / latency / judge는 Week 3 실험 A 실행 시 LangSmith run으로 수집한다. 이 문서는 형식과 기준선만 선언.

| 차원 | v1 baseline 값 | 측정 방법 |
|---|---|---|
| **Pass rate** | 27.3% (7일 실 운영) | `failure_audit.py` jobs 집계 |
| **Cost / case** | TBD (Week 3) | LangSmith run metadata (prompt + completion tokens × 모델 단가) |
| **Latency / case** | TBD (Week 3) | `@traceable` wall time |
| **Judge score** | TBD (Week 3) | 4 custom evaluator edge preservation 평균 |

**현재 부분 측정:**
- Domain QA 기준 `sorting` threshold 5.0, `graph_traversal` threshold 5.0, `cnn_param` threshold 5.0 (`qa.py:277,287,297`)
- `bfs` 1건 관찰된 QA 점수 = 3.2 (threshold 대비 −1.8)

## 6. Edge Preservation — 4개 정량 증거

GIFPT v1 코드 베이스에 **edge 소실을 방어하려는 근거 증거**가 이미 쌓여 있다. 이것이 edge-first measurement의 필요성을 뒷받침한다.

### 증거 1: `_UNKNOWN_HELPERS` 리스트 11개
**위치:** `GIFPT_AI/studio/ai/llm_codegen.py:427-433`
**내용:** LLM이 hallucinate하는 helper 함수 이름 11개를 블랙리스트화하고, `post_process_manim_code`에서 이들 호출을 `self.wait(0.1)`로 치환.

```python
_UNKNOWN_HELPERS = [
    'AddPointToGraph', 'PlotPoint', 'CreateGraph', 'AnimateCurvePoint',
    'DrawArrowBetween', 'ShowValueOnPlot',
    'Highlight', 'Focus', 'Emphasize',
    'MobjectTable', 'IntegerTable',
]
```

**Edge 해석:** `anim→codegen` edge에서 scene descriptor가 없는 operation을 codegen이 상상력으로 helper를 지어낸다. v1은 **소실 자체를 막지 못하고 하류에서 블랙리스트 패치**하는 방어 전략.

### 증거 2: `_INVALID_COLOR_MAP` 15개
**위치:** `GIFPT_AI/studio/ai/llm_codegen.py:409-425`
**내용:** LLM이 잘못 쓰는 색상 이름 15개를 Manim 유효 색상으로 매핑하는 regex replace.

**Edge 해석:** `anim→codegen`에서 색상 정보가 표준화되지 않은 채 넘어간다. `post_process_manim_code`가 **color regex × 15 + helper regex × 11 = 26개 후처리 규칙**을 집행한다. 이 숫자 자체가 "edge에서 정보가 구조화되어 넘어가지 않았다"는 증거.

### 증거 3: `sorting.comparison_shown` 페널티 −2.5
**위치:** `GIFPT_AI/studio/ai/qa.py:281`

```python
{"key": "comparison_shown",
 "desc": "Comparison or swap operations are animated step by step",
 "penalty": 2.5},
```

**Edge 해석:** `render→qa` edge에서 "sorting 영상인데 비교 연산이 애니메이션되지 않음"을 2.5점 페널티로 감지. 즉 anim_ir는 compare 연산을 명시했지만 codegen이 이를 애니메이션으로 번역하지 못했거나, anim_ir가 애초에 compare 연산을 명시하지 않은 것. v1은 **하류(QA)에서 역추적**으로 페널티를 부과하는 방식.

### 증거 4: LSM-Tree 오분류 자체 방지 주석
**위치:** `GIFPT_AI/studio/video_render.py:311-313`

```python
# Domain classification is intentionally skipped here. It caused misclassification
# crashes (e.g., LSM-Tree → sorting → empty trace → Manim crash). The generic
# pipeline handles all algorithm types through the IR abstraction.
```

**Edge 해석:** `pseudo→anim` edge에서 도메인 분류기가 LSM-Tree를 sorting으로 오분류 → anim_ir 생성 시 sorting 템플릿을 적용 → 빈 trace → Manim crash. **개발자가 도메인 분류 feature 자체를 제거**하는 것으로 해결. 이 주석은 edge 소실이 production crash로 이어졌고 근본 fix가 없어서 feature를 포기했다는 증거.

## 7. 4증거 요약표

| # | 증거 | Edge | Defense 전략 | 위치 |
|---|---|---|---|---|
| 1 | `_UNKNOWN_HELPERS` (11개 블랙리스트) | `anim→codegen` | Post-process regex로 helper 치환 | `llm_codegen.py:427` |
| 2 | `_INVALID_COLOR_MAP` (15개 color 매핑) | `anim→codegen` | Post-process regex replace | `llm_codegen.py:409` |
| 3 | `comparison_shown -2.5` 페널티 | `render→qa` | 하류에서 역추적 페널티 | `qa.py:281` |
| 4 | LSM-Tree 오분류 → feature 제거 | `pseudo→anim` | Feature 포기 | `video_render.py:311` |

## 8. 해석

v1은 **edge 소실을 모니터링할 도구가 없는 상태에서** 각 edge별로 임시방편 방어 코드(블랙리스트, regex, 페널티, feature 제거)를 쌓아왔다. `post_process_manim_code`는 26개의 regex 규칙이 한 함수에 모인 "증상 치료" 집합이며, `DOMAIN_QA_CONFIG`는 "어떤 edge가 소실되면 QA가 거부해야 하는지"를 수동 룰로 인코딩한다.

**문제:**
1. 새 도메인이 추가되면 각 edge 방어 로직을 또 손수 확장해야 한다 (scale 안 됨).
2. 어느 방어 규칙이 얼마나 효과적인지 **측정되지 않는다** — regex 하나 지우면 어떤 case가 깨지는지 모른다.
3. `post_process_manim_code`의 26개 규칙 중 "실제로 발동한 적 있는" 규칙이 몇 개인지 로그에 없다 (data-driven pruning 불가).

이것이 Phase 1에서 **LangSmith 4 custom evaluator + run diff**를 도입하는 이유다:
- Evaluator가 각 edge의 preservation을 정량화하고,
- Run diff가 "이 변경으로 어느 edge가 더 잘 / 못 보존되었나"를 즉시 드러낸다.

## 9. 다음 단계

- [ ] Week 1 말: `edge-first-measurement.md` 완성 후 Gate 1 review
- [ ] Week 2: 4 LangSmith evaluator 구현 (각 edge 하나씩)
- [ ] Week 3 실험 A: 이 4차원 벡터의 cost/latency/judge 실제 수치 채움
- [ ] Week 5 실험 B: v2 Edge preservation fail rate vs v1 — **D 결정에 따라 −30% 이상 감소 시 v2 default 스위칭**

---

**참조:**
- `failure-taxonomy.md` — 재분류 근거
- `GIFPT_AI/reports/failure_audit_2026-04-09.md` — raw data
- `scripts/README.md:103-104` — "CI regression tests are a separate piece of work"
