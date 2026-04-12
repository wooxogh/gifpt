# Archive

이 디렉토리의 문서들은 **2026-04-12** 프로젝트 방향 전환으로 superseded됨.

## 아카이브된 문서

| 문서 | 작성 시점 | 핵심 기여 (new plan에 보존) | 버려진 부분 |
|---|---|---|---|
| `harness-ci-narrative.md` | 2026-04-12 오전 | Delta-over-quality axiom, Phase 0 narrative 산출물 개념, judge self-calibration | "2주 vs 6-8주 narrative 비용표" (도구 빌드 전제라 더 이상 해당 없음) |
| `harness-ci-plan-v2.md` | 2026-04-12 오후 | Edge-first axiom, Dynamic graph data model, GIFPT v2 Level 2 아키텍처, IntentTracker 설계, 3 실험(A/B/C) 설계, GIFPT 파일 인덱스 | Harness CI 리포 bootstrap, SQLite 스키마, Adapter protocol, OpenAI VCR 설계, Django/Celery ADR, 15주 플랜, 오픈소스 공개 |

## Pivot 이유 (요약)

Day 0 Build-vs-Buy 스파이크 (`../../docs/build-vs-buy-spike.md`)에서 발견된 사실:

1. LangSmith가 run-over-run diff, golden set regression, CI 통합, per-step evaluation을 이미 제공
2. Edge-level semantic preservation assertion만 LangSmith에 내장되어 있지 않음 — 그러나 custom code evaluator 4개로 2주 내 구현 가능
3. "공백 포지션"이라는 원래 narrative 가정이 부정확함 확인
4. 15주 도구 빌드 → 6주 GIFPT 개선으로 scope 재정의가 더 강한 narrative + 더 나은 현실적 선택

## 살아남은 것 (95%)

- 3 Axiom (delta / edge-first / dynamic graph) — 그대로 유지
- 프록시 메트릭 사다리 — LangSmith custom evaluator로 구현 형태만 변경
- Failure taxonomy + v1 baseline 측정 — Phase 0 그대로
- GIFPT v2 Level 2 agentic loop + IntentTracker — Phase 2 그대로
- Judge self-calibration (20 golden edge) — Phase 2 그대로
- `scripts/README.md:103-104` 인용문 narrative asset — 보존

## 버려진 것 (5%)

- "내가 도구를 만들었다" narrative → "측정 기반으로 내 시스템을 고쳤다"로 대체
- Harness CI 독립 리포 + GitHub Action + 오픈소스 공개
- SQLite 스키마 v0, Adapter protocol, OpenAI VCR 직접 구현
- Django + Celery 기반 분산 실행 (LangSmith가 처리)
- 두 번째 어댑터 (일반화 증명)
- Velog 3부작 → 블로그 1편으로 축소

## Canonical 문서

- **프로젝트 플랜:** `../gifpt-measurement-driven-refactor.md`
- **실행 체크리스트:** `../plan.md`
- **의사결정 기록:** `../../docs/build-vs-buy-spike.md`

이 세 문서가 현재 active. 이 아카이브는 역사 보존 + 맥락 복원 용도로만 유지.
