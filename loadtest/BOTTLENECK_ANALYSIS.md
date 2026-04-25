# GIFPT Polling Layer — Bottleneck Analysis

**환경:** MacBook Air M2 (arm64) · Docker Desktop · Spring Boot 3.5.7 · MySQL 8 · Redis 7
**기준 런:** `results/baseline/phase2/run4-20260422-175509` (25.5분, 800 VU 피크)
**목적:** 이전 12회 런에서 관측된 http max 72~113초 stall의 원인 규명

## 요약

**병목 = Tomcat 스레드풀 + Hikari 커넥션풀 동시 포화** (스파이크 트래픽 구간)

Tomcat max-threads=200, Hikari maxPoolSize=10 기본값이 800 VU 부하의 스파이크에서 한계 도달. MySQL은 여유, JVM GC는 소규모 기여자.

## 측정 준비

기존 actuator는 403으로 차단되어 Tomcat/Hikari/JVM 시계열 수집 실패. 아래 변경 후 재측정:

1. **`LoadtestActuatorSecurity.java`** 추가 (`@Profile("loadtest")`, HIGHEST_PRECEDENCE SecurityFilterChain): `/actuator/**` permitAll — 프로덕션 영향 없음.
2. **`collect_metrics.sh`** 수정: 메트릭 통계 필드 매핑 수정 (`http.server.requests.active`는 `ACTIVE_TASKS`, `jvm.gc.pause`는 `TOTAL_TIME`/`MAX` 사용).

## 핵심 지표 (run 4, 150 샘플)

| 지표 | 평균 | 중앙값 | p95 | 최대 | 판정 |
|---|---:|---:|---:|---:|:---:|
| `http.server.requests.active` (동시 요청) | 3.6 | 1 | 7 | **199** | **Tomcat 200 한계 근접** |
| `jvm.threads.live` | 104 | 96 | 236 | 240 | Tomcat 동적 확장 흔적 |
| `hikari.connections.active` | 0.45 | 0 | 4 | 10 | **maxPoolSize 도달** |
| `hikari.connections.pending` | 0.15 | 0 | 0 | **11** | **DB 커넥션 대기 발생** |
| `hikari.connections.timeout` (누적) | — | — | — | 0 | 타임아웃 없음 (블록만) |
| `jvm.gc.pause` per 5s interval (s) | 0.07 | 0.018 | 0.19 | 2.91 | 대체로 건강 |
| `jvm.gc.pause` max 단일 (s) | 0.185 | 0.132 | 0.45 | **0.757** | 간헐적 긴 pause |
| `jvm.memory.used` (MB) | 323 | 321 | 399 | 467 | 정상 범위 |
| `mysql.threads_running` | 2.1 | 2 | 3 | 7 | **MySQL 무죄** |

- GC 500ms 초과 구간: 3/149 (2.0%)
- GC 1s 초과 구간: 2/149 (1.3%)
- HTTP active > 50: 2/150 (1.3%)
- HTTP active > 100: 1/150
- Hikari pending > 0: 3/150

## 병목 발생 순간의 타임라인 (18:14 UTC)

```
ts        http_active  threads_live  hikari_act  hikari_pend  gc_total  mem_MB
18:14:10          1          125           2           0         5.13      336
18:14:16         12          145           0           0         5.39      395   ← 트래픽 급증 시작
18:14:32        199          240           9           8         7.65      307   ← 병목 순간
18:14:42         69          240           7          11         7.79      418   ← DB 큐잉 지속
18:19:33          1          236           0           0        10.69      365   ← 5분 후 회복
```

**해석:**

1. `18:14:10 → 18:14:32` (22초): 동시 요청 **1 → 199** 로 폭증. Tomcat이 스레드를 125 → 240개로 급격히 생성.
2. `18:14:32`: Tomcat active 199 (≈ max 200), Hikari active 9/10 + pending 8.
3. `18:14:42`: HTTP active 69로 줄었지만 Hikari pending 11로 증가 — 대기 큐가 누적 중.
4. `18:19:33` (5분 후): 시스템 회복. jvm.threads.live=236으로 여전히 풀 보유.

## 이전 실험에서 본 max latency 72~113초의 정체

피크 순간에 요청이 병목 뒤에 쌓이면서:
- Tomcat 스레드풀 포화 → 신규 요청이 connector accept queue 에서 대기
- Hikari pending=11 → DB 호출 필요한 요청 11개가 블록
- 가장 늦은 요청은 **대기 큐 + Hikari 대기 + GC pause**를 누적 경험 → 수십 초 stall

이 패턴이 `http_req_duration.max = 72~113초` 값을 완벽히 설명.

## 반증된 가설

| 가설 | 관측 증거 | 결론 |
|---|---|---|
| MySQL 포화 | `threads_running` 최대 7 (500 중) | ❌ 무죄 |
| JVM GC 지옥 | 전체 GC 시간 11.1초 / 25.5분 = 0.73% | ❌ 주범 아님 (가끔 2.9s 스파이크만) |
| Redis 캐시 M2 역효과 | redis_cache run3 poll 체크 2,820/276k (99% 실패) | ❌ 측정 자체가 오염된 것 — 다른 병목의 결과 |

## 개선 제안

### 즉시 적용 가능 (application-loadtest.yml)

```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 30  # 기본 10 → 30
      minimum-idle: 10
server:
  tomcat:
    threads:
      max: 400  # 기본 200 → 400
      min-spare: 50
    accept-count: 200  # connector queue 여유
```

**근거:**
- Hikari 30: 피크 pending 11 해소 + 여유. MySQL max_connections=500이라 충분히 안전
- Tomcat 400: 피크 199 대비 2배 헤드룸
- accept-count 200: Tomcat 스레드 풀 초과 시 큐잉으로 연결 유지

### 후속 조치

1. **위 설정으로 Phase 2 재측정 3회** — 개선 효과 정량화 (p99/max 감소 여부)
2. **Redis 캐시 재평가** — 병목이 제거된 상태에서 캐시 가치 다시 측정 (기존 결론 뒤집힐 수 있음)
3. **JVM heap 확인** — max 467MB 관측, 컨테이너 할당 확인 후 필요 시 -Xmx 상향
4. **프로덕션(EC2) 기본값 검토** — 동일 기본값이면 동일 병목 재현 가능

## 현재 실험의 pass/fail 재해석

지금까지 RESULTS.md의 "PASS" 판정은 **threshold(p95<2s, error rate<5%)**를 통과했다는 의미. 하지만 max latency 수십 초 + 런 간 30배 처리량 편차는 **시스템이 불안정**했다는 신호였음. 개선 설정 적용 후 재측정 시 해당 불안정성이 사라지는지 확인 필요.

## 산출물

- `results/baseline/phase2/run4-*/metrics.csv` — Spring 메트릭 포함된 첫 번째 런
- `GIFPT_BE/src/main/java/com/gifpt/security/auth/config/LoadtestActuatorSecurity.java` — 프로파일 스코프 actuator 허용
- `loadtest/collect_metrics.sh` — 메트릭 통계 필드 매핑 수정

---

*분석 시점: 2026-04-23 · M2 단일 호스트 · 프로덕션 수치 아님*
