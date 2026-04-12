# GIFPT Harness CI — 프로젝트 narrative 및 실행 전략

> 2026-04-12 대화 정리본. 목적: (1) 면접에서 쓸 narrative 확정, (2) Harness CI 도구를 만들지/얼마나 만들지 결정, (3) 최소 비용으로 면접 Ready 라인 도달.

---

## 0. TL;DR

1. **프로젝트의 진짜 장점**은 "기술적 미숙함을 학습으로 메꿨다"가 아니라 **"측정 없이 움직이지 않는 엔지니어링 규율"**이다.
2. 영상 품질은 단일 숫자로 측정 불가능하다. 그래서 **quality를 포기하고 delta(회귀)를 측정**하는 쪽으로 문제를 재정의한다.
3. **면접 Ready 라인이 2개** 있다:
   - **2주 버전** (저비용·정직): v1 해부 + failure taxonomy + proxy metric ladder 문서화. 이미 enough.
   - **6~8주 버전** (고비용·완결): v1 vs v2 회귀 리포트까지. 원래 플랜.
4. **순서 역전**: Harness CI 풀버전을 짓기 전에 **Phase 0 (2주 narrative 산출물)**을 먼저 만든다. 그 후 Phase 1 풀빌드를 할지, GIFPT 본체에 시간을 더 쓸지 결정한다.

---

## 1. Narrative 재프레이밍 — 주니어 vs 시니어

같은 행동도 프레이밍에 따라 면접관이 듣는 시그널이 완전히 다르다.

| | 주니어 narrative | 시니어 narrative |
|---|---|---|
| 동기 | "몰라서 많이 찾아봤다" | "측정 없이는 리팩터 안 한다" |
| 포지션 | 호기심 / 학습자 | Engineering discipline |
| 희소성 | 흔함 | 드묾 |
| 증거 | 학습 흔적 | 측정 인프라 + 리포트 |

**핵심 문장** (면접에서 한 줄만 기억한다면):

> "저는 측정할 수 없는 것을 측정하려고 시간을 쓰지 않습니다. 대신 **측정할 수 있는 것만으로 의사결정이 가능하도록 문제를 재정의**합니다."

---

## 2. 영상 품질 측정 문제의 해부

### 2.1 핵심 insight

> "영상 품질은 자동으로 측정 못 합니다. 그래서 저는 품질을 측정하려 하지 않고, **품질의 변화(delta)**를 측정하는 쪽으로 문제를 재정의했습니다."

이 재정의가 강력한 이유: "못 푸는 문제를, 풀 수 있는 더 작은 문제로 바꿀 줄 안다" — 시니어 엔지니어의 핵심 스킬.

### 2.2 Proxy metric ladder

quality라는 단일 메트릭을 포기하고 사다리를 만든다:

| 층 | 측정 대상 | 난이도 | 자동화 |
|---|---|---|---|
| **Stage 1 파싱** | LLM 출력이 valid JSON인가 | 쉬움 | 100% |
| **Stage 2 계획** | 계획이 알려진 helper만 참조하는가 (`_UNKNOWN_HELPERS`) | 쉬움 | 100% |
| **Stage 3 코드 생성** | Manim 코드가 compile + run 되는가 | 중간 | 100% |
| **Stage 4 렌더** | ffmpeg가 valid mp4를 만드는가, duration이 정상 범위인가 | 중간 | 100% |
| **구조적** | 출력 다양성 (시각적 스타일 collapse 감지) | 중간 | 80% |
| **의미적** | 영상이 실제로 개념을 설명하는가 | 어려움 | LLM-as-judge + 샘플링 |
| **미적/교육적** | "좋은 영상인가" | 불가능 | 10% 수동 샘플링 |

**프레이밍**: "quality를 한 숫자로 요약하는 건 거짓말이라 판단했습니다. 자동화 가능한 95%를 메트릭 레이어로 쌓고, 불가능한 5%는 리포트에 샘플 10개 랜덤 선택해서 수동 확인하는 쪽으로 scope을 좁혔습니다."

### 2.3 Regression > Quality (가장 중요한 재정의)

> "절대 품질은 측정 못 해도, 같은 input에서 v1 → v2로 넘어갔을 때 출력이 어떻게 변했는가는 측정할 수 있습니다. **회귀 감지는 품질 추정보다 훨씬 싼 문제**입니다."

구체적 증거물:
- **Determinism 검증**: seed 고정 후 같은 input 2번 실행 → diff가 0이 아니면 flakiness 경고
- **레퍼런스 diff**: v1 baseline vs v2 output을 stage별 비교 → attribution
- **Failure class migration**: "v1에서 60%였던 `_UNKNOWN_HELPERS`가 v2에서 5%로, 그러나 v1에 없던 `_TIMEOUT` 실패가 v2에서 12% 등장" — **고친 버그와 새로 생긴 버그를 분리**

결과 보고 스타일:
> "v2가 더 좋은지 나쁜지 단일 숫자로 말할 수 없었지만, '기존 실패 92% 감소 + 새 실패 12% 등장 + 토큰 40% 증가 + 물리 도메인에서 회귀'라는 **4차원 벡터로 보고**했습니다. 단일 숫자는 거짓말이지만 이 벡터는 실제 의사결정을 가능하게 했습니다."

### 2.4 LLM-as-judge의 메타 문제 (정직성 증명)

의미적 평가는 LLM-as-judge로 자동화 가능하지만, judge 자체도 측정 대상이다:
- Judge 모델 버전이 바뀌면 판정도 바뀐다 (judge drift)
- Judge의 편향을 모르면 숫자도 신뢰 불가

해결: **20개 수동 라벨링된 golden sample로 calibrate**. Agreement ≥ 85%일 때만 자동 판정을 신뢰.

이 디테일의 가치: **자신의 메트릭을 불신할 줄 아는 능력**. 메트릭 만드는 사람은 많지만, 자기 메트릭을 calibrate하는 사람은 드물다.

---

## 3. 면접 narrative arc (3분 버전)

1. **Problem**: "GIFPT 4-stage LLM 영상 생성 파이프라인을 만들었는데, v1이 brittle하다는 건 느꼈지만 '어디서 얼마나' 브리틀한지 몰랐습니다."
2. **첫 시도와 실패**: "처음엔 end-to-end 'quality score'를 만들려다 실패했습니다. 영상 품질은 단일 숫자로 요약 불가능하다는 걸 깨달았습니다."
3. **재정의**: "quality 측정을 포기하고 **delta 측정**으로 문제를 바꿨습니다. 회귀 감지는 품질 추정보다 훨씬 싼 문제입니다."
4. **Build**: "Stage별 프록시 메트릭 사다리 + VCR 기반 deterministic replay + LLM-as-judge + golden sample calibration을 harness로 묶었습니다."
5. **Result**: "v1 vs v2 리포트가 'v2는 기존 실패 92% 감소, 새 실패 12% 등장, 토큰 40% 증가, 물리 도메인에서 회귀'였습니다. 이 4차원 벡터를 보고 **agency를 chemistry stage에만 주기로** 결정했습니다."
6. **Reflection**: "측정 못 하는 문제를 풀려 하지 말고, 풀 수 있는 더 작은 문제로 재정의하는 것 — 이게 LLM 엔지니어링에서 가장 rare한 스킬이라고 생각합니다."

**마무리용 일반화**:
> "LLM 엔지니어링이 2010년대 DevOps의 관측성(observability) 전환과 같은 지점에 있다고 봅니다. 당시 엔지니어들은 '내 서버가 느려졌다'를 vibe로 판단하다 Prometheus/Grafana로 넘어갔습니다. 지금 LLM 개발자들은 '내 프롬프트가 더 좋아졌다'를 vibe로 판단합니다. 이 전환이 곧 온다고 보고 GIFPT에서 먼저 겪어본 겁니다."

---

## 4. Narrative 조각별 비용표 (가장 실용적)

**narrative 조각마다 면접에서 말하려면 최소 얼마나 해야 하는가**가 다르다. 전부 만들 필요 없음.

| narrative 조각 | 최소 필요 작업 | 비용 |
|---|---|---|
| "quality는 단일 숫자로 못 판다 → delta로 재정의" | 결정 + 이유 정리. **코드 0줄.** | 지금 당장 |
| "Stage별 failure taxonomy를 만들었다" | `failure_audit.py` 결과를 분류 체계로 문서화 | 2~3일 |
| "v1의 실패 분포를 정량 측정했다" | 기존 16 케이스에 taxonomy 돌리기 | +2일 |
| "proxy metric ladder 설계" | 사다리를 README 한 장으로 정리 | +반나절 |
| "v1 vs v2 회귀 attribution" | v2 존재 + harness 실행 + 리포트 | **3~5주** |
| "LLM-as-judge calibration" | golden sample + agreement 측정 | +1~2주 |
| "LLM observability 트렌드론" | 결정 + 한 문단. **코드 0줄.** | 지금 당장 |

**핵심 관찰**: 위쪽 4개는 **2주 안에** 전부 달성 가능. 코드 대부분은 이미 GIFPT에 있음 (`failure_audit.py`, 16 케이스, 4-stage 파이프라인, weekly_audit 로그). **없는 건 "문서화된 결과" 한 장뿐.**

---

## 5. 실행 전략: Phase 0 → Phase 1

### Phase 0 — 2주 narrative 산출물 (먼저 할 것)

**목표**: 면접에서 말할 수 있는 최소 증거물을 만든다. Harness CI 풀빌드 없이.

1. **Failure taxonomy 문서** — `failure_audit.py`가 찾는 실패 유형을 분류 체계로 정리. 카테고리 예: `_UNKNOWN_HELPERS`, `_TIMEOUT`, `_JSON_PARSE_FAIL`, `_COMPILE_FAIL`, `_RENDER_FAIL`, `_SEMANTIC_DRIFT`.
2. **v1 baseline 측정** — 16 케이스 × 현재 파이프라인 → stage별 pass/fail + failure class 분포를 표로.
3. **Proxy metric ladder README** — 섹션 2.2 표를 GIFPT context에 맞춰 한 문서로.
4. **Weekly audit 실패 20개 수동 검토** — production 실패를 읽고 taxonomy가 커버하는지 확인. 커버 안 되는 건 새 카테고리 추가.

**산출물**:
- `docs/failure-taxonomy.md`
- `docs/v1-baseline-report.md` (숫자 있는 한 장)
- `docs/measurement-philosophy.md` (proxy ladder + delta vs quality 철학)

**이 정도면 2주 버전 narrative는 완성**이고, 면접에서 이미 작동한다:

> "v1을 정량 해부했고, v2로 넘어가기 전에 측정 기반을 깔았습니다. 다음 단계는 자동화 harness로 v1/v2 회귀 리포트를 만드는 건데, 이건 지금 진행 중입니다."

"진행 중"이라고 솔직하게 말하는 쪽이 "다 끝났다"보다 **신뢰도 더 높다**. 시니어일수록 "완료된 프로젝트"보다 "현재 씨름 중인 문제"에 관심 있다.

### Phase 1 — Harness CI 풀빌드 (할지 여부는 Phase 0 후 결정)

Phase 0 결과를 보고 다음 질문에 답한다:
> **"내가 GIFPT에 다음 프롬프트 변경 3개를 할 때, 이 도구 없이 판단 가능한가?"**
>
> - 차이가 "20분 vs 3시간" → 풀빌드 할 가치 있음
> - 차이가 "5분 vs 20분" → 기존 도구(promptfoo / Inspect / LangSmith)나 주피터 노트북으로 충분

---

## 6. 원래 8주 플랜 비판 요약

원래 제시된 8~10주 플랜에 대한 유보사항 기록 (재검토 시 참고용):

### 6.1 찬성한 결정

- **OpenAI VCR을 Week 2 최우선** — 캐시 없으면 eval 비용이 며칠 안에 폭발. 강하게 동의.
- **GIFPT-only 먼저, Week 7에 추상화** — premature abstraction 방지 맞음.
- **SQLite 단일 파일** — 초기 단계에 합리적.

### 6.2 유보/반대한 결정

1. **Django REST + Celery는 over-engineering**
   - "GIFPT를 import한다"는 요건만으론 Pure Python CLI + SQLite + `multiprocessing.Pool`로 충분.
   - Django는 migrations/settings/admin 등 부수 복잡도를 끌고 와서 Week 1~2를 먹음.
   - HTTP/대시보드가 실제 필요해지는 시점(빨라도 Week 7)에 얹는 게 안전.

2. **없는 ADR이 제일 중요**
   - "직접 만들기 vs promptfoo / Inspect / LangSmith / Weave 사용"이 논의에 없음.
   - 10주는 GIFPT 본체에 안 쓰는 시간. Day 0에 30분만 기존 도구 + 200줄 어댑터로 80% 해결이 안 되는지 확인할 가치 있음.
   - 이 질문 없이 Day 1로 넘어가면 "eval 도구를 만드느라 eval할 GIFPT 개선이 멈췄다"는 전형적 함정에 빠짐.

3. **16 케이스로 "회귀 감지" 주장은 위험**
   - 신호/노이즈 구분이 어려움.
   - **옵션 B (weekly_audit 실패 20개 추가)를 Week 1에 당겨오는 쪽이 낫다.**

4. **Week 9 공개 launch를 고정 목표로 두지 말 것**
   - 공개 압박이 도구 자체의 가치 판단을 왜곡함.
   - 도구가 본인한테 먼저 value를 준 뒤 공개 여부를 결정하는 순서가 맞음.
   - Velog 3부작은 Week 6~7의 실제 실험 결과를 보고 쓸지 결정.

---

## 7. 결론: 지금 당장 할 것

1. **이 문서를 읽고** 2주 버전 narrative가 충분한지 스스로 판단.
2. **Phase 0 산출물 3개** (`failure-taxonomy.md`, `v1-baseline-report.md`, `measurement-philosophy.md`)를 2주 안에 만든다.
3. 그 후 다시 질문: "Harness CI 풀빌드 할 가치 있나?" — 이 질문에 답하기 전에 Phase 1을 시작하지 말 것.
4. **도구가 아니라 리포트 한 장이 실제 면접 asset**이라는 것을 잊지 말 것.

---

## 부록: 한 줄 요약 모음 (필요 시 복붙용)

- "측정 없이는 리팩터 안 한다 — 이게 제 엔지니어링 규율입니다."
- "quality를 측정하려 하지 않고, quality의 delta를 측정하도록 문제를 재정의했습니다."
- "단일 숫자는 거짓말이지만, 4차원 벡터는 실제 의사결정을 가능하게 했습니다."
- "자동화 가능한 95%를 메트릭 레이어로 쌓고, 불가능한 5%는 수동 샘플링으로 scope을 좁혔습니다."
- "LLM 엔지니어링은 2010년대 DevOps 관측성 전환과 같은 지점에 있다고 봅니다."
- "저는 측정할 수 없는 것을 측정하려고 시간을 쓰지 않습니다. 대신 측정할 수 있는 것만으로 의사결정이 가능하도록 문제를 재정의합니다."
