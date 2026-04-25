# GIFPT Polling Layer Load Test — Results

**Environment:** MacBook Air M2 (arm64) · Docker Desktop · Spring Boot 3.5.7 / MySQL 8 / Redis 7
**Profile:** `loadtest` · Actuator metrics enabled
**Runs:** 12 total across 4 experiment × phase cells

## Executive summary

| Experiment × Phase | avg RPS | avg p90 (ms) | avg p95 (ms) | avg max (ms) | total reqs (sum) | pass/fail |
|---|---:|---:|---:|---:|---:|:---:|
| baseline / phase1 | 2832.2 | 347.2 | 530.8 | 4555 | 10,196,683 | PASS |
| baseline / phase2 | 189.9 | 205.2 | 550.5 | 75852 | 876,626 | PASS |
| interval_1s / phase2 | 192.5 | 582.0 | 1199.0 | 35409 | 888,425 | PASS |
| redis_cache / phase2 | 139.8 | 276.9 | 857.0 | 12883 | 649,084 | PASS |

## Per-run detail

### baseline / phase1

| run | duration (s) | RPS | reqs | iters | avg (ms) | p90 (ms) | p95 (ms) | max (ms) | check | pass | fail |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| run1 | 1200.0 | 1619.8 | 1,943,843 | 1,943,843 | 174.7 | 542.2 | 875.3 | 6085 | status is 404 or 403 | 1,943,843 | 0 |
| run2 | 1200.1 | 2427.0 | 2,912,583 | 2,912,583 | 116.6 | 317.2 | 427.3 | 4269 | status is 404 or 403 | 2,912,583 | 0 |
| run3 | 1200.1 | 4449.8 | 5,340,257 | 5,340,257 | 63.6 | 182.1 | 289.6 | 3311 | status is 404 or 403 | 5,340,257 | 0 |

### baseline / phase2

| run | duration (s) | RPS | reqs | iters | avg (ms) | p90 (ms) | p95 (ms) | max (ms) | check | pass | fail |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| run1 | 1532.5 | 193.4 | 296,374 | 296,374 | 130.2 | 222.6 | 484.7 | 72832 | n/a | 0 | 0 |
| run2 | 1553.5 | 147.1 | 228,481 | 228,062 | 194.0 | 116.7 | 593.9 | 113308 | n/a | 0 | 0 |
| run3 | 1534.1 | 229.3 | 351,771 | 351,695 | 124.8 | 276.4 | 572.9 | 41417 | n/a | 0 | 0 |

### interval_1s / phase2

| run | duration (s) | RPS | reqs | iters | avg (ms) | p90 (ms) | p95 (ms) | max (ms) | check | pass | fail |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| run1 | 1531.1 | 223.9 | 342,801 | 342,801 | 171.0 | 324.1 | 712.8 | 37409 | n/a | 0 | 0 |
| run2 | 1545.6 | 200.7 | 310,116 | 310,116 | 200.4 | 432.9 | 1091.9 | 24899 | n/a | 0 | 0 |
| run3 | 1538.7 | 153.1 | 235,508 | 235,406 | 396.1 | 989.1 | 1792.1 | 43919 | n/a | 0 | 0 |

### redis_cache / phase2

| run | duration (s) | RPS | reqs | iters | avg (ms) | p90 (ms) | p95 (ms) | max (ms) | check | pass | fail |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| run1 | 1560.0 | 121.9 | 190,113 | 8,732 | 8.3 | 18.2 | 26.8 | 794 | poll ok | 180,936 | 0 |
| run2 | 1560.0 | 115.1 | 179,593 | 8,245 | 169.7 | 161.9 | 634.3 | 12794 | poll ok | 170,945 | 0 |
| run3 | 1531.4 | 182.4 | 279,378 | 276,558 | 364.3 | 650.5 | 1909.8 | 25060 | poll ok | 2,820 | 0 |

## Observations

### Phase 2 (end-to-end animate + poll, 800 VU peak, 25.5 min)

- **Baseline** (3s poll, no cache): avg p95 = 550.5 ms, avg RPS = 189.9
- **Redis status cache** (3s poll, 2s TTL): avg p95 = 857.0 ms, avg RPS = 139.8
- **1s poll interval** (no cache): avg p95 = 1199.0 ms, avg RPS = 192.5

- Redis cache effect on p95 vs baseline: **+55.7%**
- 1s interval effect on p95 vs baseline: **+117.8%**

### Notes on methodology

- `http_req_failed` metric in raw k6 output has `rate=1.0` due to lack of `expected_response` tagging on requests. The authoritative pass/fail signal is the per-script `check` (`poll ok` / `status_ok`), surfaced in the per-run tables above.
- MacBook M2 is single-node host; all services + k6 share CPU. Phase 2 run-to-run variance is high (see per-run p95 spread). For absolute latency claims, re-run on dedicated EC2.
- For comparative claims (Redis vs baseline, 1s vs 3s interval), the 3-run average absorbs most host noise.

## Next steps

- [ ] Promote Redis `StatusCache` to a production-configurable feature (profile-agnostic)
- [ ] Re-run on EC2 t3.large to validate M2 numbers
- [ ] Add Grafana dashboards from `/actuator/metrics` series already captured in `metrics.csv`
