# Load Test Environment Snapshot

**Run date:** 2026-04-21

## Host
- Machine: MacBook M2 (Air)
- macOS: 26.3 (build 25D125)
- CPU: Apple M2 (8 cores)
- RAM: 8 GB
- Docker Desktop engine: 28.3.2

## Images (linux/arm64)
- spring: built locally from `GIFPT_BE/Dockerfile` → `gifpt-spring-loadtest:arm64`
- django: built locally from `GIFPT_AI/Dockerfile` → `gifpt-django-loadtest:arm64`
- worker: built locally from `loadtest/mock-worker/Dockerfile` → `gifpt-worker-loadtest:arm64`, concurrency=4
- mysql: mysql:8.0
- redis: redis:7
- nginx: nginx:1.27-alpine

## Spring
- Java 17 (toolchain)
- Spring Boot 3.5.7
- Profile: `loadtest`
- Actuator exposure: `health, metrics`
- Hikari default max pool size: 10 (override from running container to record actual)
  ```bash
  curl -s http://localhost:8080/actuator/metrics/hikaricp.connections.max | jq
  ```
- Tomcat default max threads: 200 (verify)
  ```bash
  curl -s http://localhost:8080/actuator/metrics/tomcat.threads.config.max | jq
  ```

## MySQL
- Version: 8.0
- `max_connections`: 500 (set in compose override command)
- `innodb_buffer_pool_size`: default (record actual)
  ```bash
  docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml exec mysql \
    mysql -uroot -ploadtest-root -e "SHOW VARIABLES LIKE 'innodb_buffer_pool_size';"
  ```

## Mock worker
- Sleep: uniform(8, 20) seconds
- Concurrency: 4
- Callback target: `http://spring:8080/api/v1/analysis/{jobId}/complete`

## k6
- Version: run `k6 version` (install via `brew install k6`)
- Install: brew

## Caveats
- No Rosetta emulation (arm64 builds), but M2 performance is not EC2 performance.
- Single-host noise: k6 + all services + macOS on one machine. Document mid-run CPU via `top -l 1`.
- This is NOT a prod-accurate absolute threshold. Values are internally consistent for comparing experiments; apply judgment when extrapolating.
- Host RAM is 8 GB — Docker Desktop memory ceiling must be ≥6 GB to accommodate MySQL + Spring + Django + worker + redis + nginx. Monitor for host swapping during high-VU stages.
