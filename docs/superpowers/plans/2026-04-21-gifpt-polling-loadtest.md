# gifpt Polling Layer Load Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a MacBook M2 load test harness for gifpt's `/animate/status` polling endpoint and run Baseline + Redis-cache + 1s-interval experiments to inform the polling-vs-push decision.

**Architecture:** A Docker Compose override layers a local MySQL 8 container and a mock Celery worker on top of the existing gifpt stack, all rebuilt for `linux/arm64` to avoid Rosetta emulation. A Spring `loadtest` profile exposes Actuator metrics without touching production config. k6 scripts drive two workloads (status-only and full-flow) against 100 seeded user accounts. A throwaway git branch carries the Redis cache patch for Experiment B and is never merged.

**Tech Stack:** Docker Compose, MySQL 8, Celery (mock), k6, Spring Boot 3.5 Actuator, Lettuce/Redis (Experiment B only), bash, Python 3.11.

**Spec:** `docs/superpowers/specs/2026-04-21-gifpt-polling-loadtest-design.md`

---

## File Structure

### New files
- `loadtest/README.md` — how to run
- `loadtest/docker-compose.loadtest.yml` — compose override (mysql + mock worker + arm64)
- `loadtest/mock-worker/Dockerfile`
- `loadtest/mock-worker/mock_tasks.py`
- `loadtest/seed_users.py`
- `loadtest/collect_metrics.sh`
- `loadtest/test-env.md`
- `loadtest/k6_status_only.js`
- `loadtest/k6_full_flow.js`
- `loadtest/run_experiment.sh`
- `loadtest/results/.gitkeep`
- `loadtest/RESULTS.md` (filled in Task 12)
- `GIFPT_BE/src/main/resources/application-loadtest.yml`

### Modified files
- `GIFPT_BE/build.gradle` — add `spring-boot-starter-actuator`
- `.gitignore` — exclude raw k6 output, keep summaries

### Experiment B only (separate branch `experiment-b/redis-status-cache`, never merged)
- `GIFPT_BE/build.gradle` — add `spring-boot-starter-data-redis`
- `GIFPT_BE/src/main/java/com/gifpt/analysis/cache/StatusCache.java` — cache wrapper
- `GIFPT_BE/src/main/java/com/gifpt/analysis/controller/AnimateController.java` — call cache
- `GIFPT_BE/src/main/resources/application-loadtest.yml` — Redis host config

### Out of scope (per spec)
- No changes to `gifpt-fe/src/hooks/useAnimate.ts` (Experiment C is k6-only)
- No changes to `studio/tasks.py` or any `studio/ai/*.py`

---

## Task 1: Scaffold loadtest directory

**Files:**
- Create: `loadtest/README.md`
- Create: `loadtest/results/.gitkeep`
- Modify: `.gitignore`

- [ ] **Step 1: Create directory structure**

Run:
```bash
cd ~/Desktop/GitHub/gifpt
mkdir -p loadtest/mock-worker loadtest/results
touch loadtest/results/.gitkeep
```

- [ ] **Step 2: Write README.md**

Create `loadtest/README.md`:

```markdown
# gifpt Polling Layer Load Test

See spec: `docs/superpowers/specs/2026-04-21-gifpt-polling-loadtest-design.md`

## Prereqs
- Docker Desktop running
- k6 (`brew install k6`)
- Python 3.11+ (for seed_users.py)

## Quickstart
```bash
# 1. Build arm64 images
docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml build

# 2. Start stack
export DB_HOST=mysql DB_USER=gifpt DB_PASSWORD=loadtest \
       GIFPT_JWT_SECRET=loadtest-secret-at-least-32-chars-long \
       GIFPT_CALLBACK_SECRET=loadtest-callback-secret \
       AWS_ACCESS_KEY_ID=fake AWS_SECRET_ACCESS_KEY=fake \
       OPENAI_API_KEY=unused \
       LOADTEST_SEED_PASSWORD=LoadTest123!

docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml up -d

# 3. Seed users
python seed_users.py

# 4. Run
./run_experiment.sh baseline phase1
```

## Artifacts
Each run lands in `results/<timestamp>/`. Final aggregation in `RESULTS.md`.
```

- [ ] **Step 3: Add loadtest .gitignore rules**

Append to `~/Desktop/GitHub/gifpt/.gitignore`:
```
# loadtest
loadtest/results/*/k6_summary.json
loadtest/results/*/metrics.csv
loadtest/tokens.json
!loadtest/results/.gitkeep
!loadtest/results/*/summary.md
```

Rationale: raw artifacts can be large; summaries commit for the record. Tokens must never commit.

- [ ] **Step 4: Commit scaffolding**

```bash
cd ~/Desktop/GitHub/gifpt
git add -f loadtest/README.md loadtest/results/.gitkeep
git add .gitignore
git commit -m "test: scaffold loadtest directory structure"
```

Expected: single commit adding loadtest scaffolding.

---

## Task 2: Build mock Celery worker

**Files:**
- Create: `loadtest/mock-worker/Dockerfile`
- Create: `loadtest/mock-worker/mock_tasks.py`

- [ ] **Step 1: Write mock_tasks.py**

Create `loadtest/mock-worker/mock_tasks.py`:

```python
"""Mock Celery task that replaces studio.animate_algorithm for load testing.

Skips OpenAI/Manim/S3. Sleeps to mimic prod render time, then hits the Spring
callback with SUCCESS + a fixture URL.
"""
import os
import random
import time
import logging
import requests
from celery import shared_task

logger = logging.getLogger(__name__)

SPRING_CALLBACK_BASE = os.environ.get("SPRING_CALLBACK_BASE", "http://spring:8080")
CALLBACK_SECRET = os.environ.get("GIFPT_CALLBACK_SECRET", "")
MIN_SLEEP = float(os.environ.get("MOCK_MIN_SLEEP_SECONDS", "8"))
MAX_SLEEP = float(os.environ.get("MOCK_MAX_SLEEP_SECONDS", "20"))
FIXTURE_URL = os.environ.get(
    "MOCK_RESULT_URL",
    "https://gifpt-demo.s3.ap-northeast-1.amazonaws.com/fixtures/loadtest.mp4",
)


@shared_task(name="studio.animate_algorithm")
def animate_algorithm(job_id: int, algorithm: str, prompt: str = None):
    delay = random.uniform(MIN_SLEEP, MAX_SLEEP)
    logger.info("mock animate_algorithm job_id=%s sleeping %.1fs", job_id, delay)
    time.sleep(delay)
    r = requests.post(
        f"{SPRING_CALLBACK_BASE}/api/v1/analysis/{job_id}/complete",
        json={"status": "SUCCESS", "resultUrl": FIXTURE_URL, "errorMessage": ""},
        headers={"X-Callback-Secret": CALLBACK_SECRET},
        timeout=10,
    )
    r.raise_for_status()
    logger.info("mock callback ok job_id=%s status=%s", job_id, r.status_code)
    return {"job_id": job_id, "status": "SUCCESS"}
```

**Note on callback payload/headers:** verify exact shape in `AnalysisCallbackController` before smoke test. Fix this task's payload if it diverges.

- [ ] **Step 2: Write Dockerfile**

Create `loadtest/mock-worker/Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir celery==5.3.6 redis==5.0.1 requests==2.32.3
COPY mock_tasks.py /app/studio/__init__.py.tmp
RUN mkdir -p /app/studio && mv /app/studio/__init__.py.tmp /app/studio/__init__.py && \
    cp /app/studio/__init__.py /app/studio/tasks.py
# Celery app discovers studio.animate_algorithm
ENV PYTHONPATH=/app
CMD ["celery", "-A", "studio.tasks", "worker", "-l", "info", "-Q", "gifpt.default", "--concurrency=4"]
```

Rationale: a minimal Celery runner that registers only the mock task. No Django, no Manim, no OpenAI, no boto3. Concurrency 4 per spec §3.

- [ ] **Step 3: Verify the exact callback contract**

Find the callback controller:
```bash
cd ~/Desktop/GitHub/gifpt
grep -rn "analysis/{.*}/complete\|analysisComplete\|callback.*secret" GIFPT_BE/src/main/java
```

Read the endpoint handler and match `mock_tasks.py`'s payload keys and the header name exactly (common variants: `X-Callback-Secret`, `X-Internal-Secret`, body field `resultUrl` vs `result_url`).

- [ ] **Step 4: Fix mock_tasks.py if contract differs**

Edit the `requests.post(...)` call to match. Rerun Step 3's grep to confirm.

- [ ] **Step 5: Commit**

```bash
git add -f loadtest/mock-worker/Dockerfile loadtest/mock-worker/mock_tasks.py
git commit -m "test: add mock Celery worker for loadtest"
```

---

## Task 3: Add Spring loadtest profile + Actuator

**Files:**
- Modify: `GIFPT_BE/build.gradle`
- Create: `GIFPT_BE/src/main/resources/application-loadtest.yml`

- [ ] **Step 1: Add Actuator dependency**

Edit `GIFPT_BE/build.gradle`, add inside `dependencies { ... }`:

```gradle
	implementation 'org.springframework.boot:spring-boot-starter-actuator'
```

Place it next to the other `spring-boot-starter-*` lines.

- [ ] **Step 2: Create application-loadtest.yml**

Create `GIFPT_BE/src/main/resources/application-loadtest.yml`:

```yaml
spring:
  datasource:
    url: jdbc:mysql://${DB_HOST}:3306/gifpt?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Seoul
    username: ${DB_USER}
    password: ${DB_PASSWORD}
  jpa:
    hibernate:
      ddl-auto: update
    properties:
      hibernate:
        format_sql: false
  sql:
    init:
      mode: never

logging:
  level:
    org.hibernate.SQL: warn
    org.hibernate.orm.jdbc.bind: warn
    com.zaxxer.hikari: info
    root: warn

management:
  endpoints:
    web:
      exposure:
        include: health, metrics
  metrics:
    tags:
      application: gifpt-loadtest
  endpoint:
    metrics:
      enabled: true

# Reuse all other gifpt.* settings from application.yml via profile merge.
```

Rationale: mirrors `application-docker.yml` but silences verbose SQL logging (noise at 800 VU) and exposes `/actuator/metrics`. No prod secrets here.

- [ ] **Step 3: Verify Gradle syntax**

```bash
cd ~/Desktop/GitHub/gifpt/GIFPT_BE
./gradlew help --quiet
```

Expected: no error. (Takes ~20s to resolve deps.)

- [ ] **Step 4: Smoke-check Actuator compiles**

```bash
./gradlew build -x test --quiet 2>&1 | tail -5
```

Expected: `BUILD SUCCESSFUL`.

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/GitHub/gifpt
git add GIFPT_BE/build.gradle GIFPT_BE/src/main/resources/application-loadtest.yml
git commit -m "test: add Spring loadtest profile with Actuator exposure"
```

---

## Task 4: Compose override (MySQL + mock worker + arm64)

**Files:**
- Create: `loadtest/docker-compose.loadtest.yml`

- [ ] **Step 1: Write compose override**

Create `loadtest/docker-compose.loadtest.yml`:

```yaml
# Usage:
#   docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml up -d
#
# Overrides for local MacBook M2 load testing:
# - Adds local mysql container (prod uses RDS)
# - Replaces Celery worker with mock (no OpenAI/Manim)
# - Switches all services to linux/arm64 (no Rosetta)
# - Switches Spring to 'loadtest' profile

services:
  mysql:
    image: mysql:8.0
    platform: linux/arm64
    environment:
      MYSQL_ROOT_PASSWORD: loadtest-root
      MYSQL_DATABASE: gifpt
      MYSQL_USER: ${DB_USER}
      MYSQL_PASSWORD: ${DB_PASSWORD}
    ports:
      - "3306:3306"
    volumes:
      - ./results/mysql-data:/var/lib/mysql
    command: >-
      --character-set-server=utf8mb4
      --collation-server=utf8mb4_unicode_ci
      --max-connections=500

  spring:
    platform: linux/arm64
    build:
      context: ../GIFPT_BE
      dockerfile: Dockerfile
    environment:
      SPRING_PROFILES_ACTIVE: loadtest
      DB_HOST: mysql
    depends_on:
      - mysql
      - redis

  django:
    platform: linux/arm64
    build:
      context: ../GIFPT_AI
      dockerfile: Dockerfile

  worker:
    platform: linux/arm64
    build:
      context: ./mock-worker
      dockerfile: Dockerfile
    environment:
      SPRING_CALLBACK_BASE: http://spring:8080
      GIFPT_CALLBACK_SECRET: ${GIFPT_CALLBACK_SECRET}
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/1
      MOCK_MIN_SLEEP_SECONDS: "8"
      MOCK_MAX_SLEEP_SECONDS: "20"
    command: celery -A studio.tasks worker -l info -Q gifpt.default --concurrency=4
    depends_on:
      - redis
      - spring

  redis:
    platform: linux/arm64

  nginx:
    platform: linux/arm64
```

- [ ] **Step 2: Verify Spring Dockerfile exists**

```bash
ls GIFPT_BE/Dockerfile
```

Expected: file exists. If missing, the existing prod pipeline must be pushing pre-built images — in that case, keep the `image:` line from the original compose and skip the local `build:` block. Adjust override accordingly.

- [ ] **Step 3: Smoke-validate compose config**

```bash
cd ~/Desktop/GitHub/gifpt/loadtest
export DB_HOST=mysql DB_USER=gifpt DB_PASSWORD=loadtest \
       GIFPT_JWT_SECRET=loadtest-secret-at-least-32-chars-long \
       GIFPT_CALLBACK_SECRET=loadtest-callback-secret \
       AWS_ACCESS_KEY_ID=fake AWS_SECRET_ACCESS_KEY=fake \
       OPENAI_API_KEY=unused
docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml config --quiet
```

Expected: no error output. (Missing env vars or bad YAML will print warnings.)

- [ ] **Step 4: Commit**

```bash
cd ~/Desktop/GitHub/gifpt
git add -f loadtest/docker-compose.loadtest.yml
git commit -m "test: compose override for arm64 + local mysql + mock worker"
```

---

## Task 5: Build arm64 images and smoke-up the stack

**Files:** none modified. Runtime verification only.

- [ ] **Step 1: Build all images**

```bash
cd ~/Desktop/GitHub/gifpt/loadtest
docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml build 2>&1 | tail -30
```

Expected: three images build (`spring`, `django`, `worker`). First build can take 5–10 minutes (TeX install in Django image). Retry if network flakes.

- [ ] **Step 2: Start the stack**

```bash
docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml up -d
docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml ps
```

Expected: all six services (`redis`, `mysql`, `spring`, `django`, `worker`, `nginx`) in `running` state.

- [ ] **Step 3: Verify Spring Actuator reachable**

```bash
curl -s http://localhost:8080/actuator/health
curl -s http://localhost:8080/actuator/metrics/tomcat.threads.busy | head -c 200
```

Expected:
- `/health` returns `{"status":"UP"}`
- `/metrics/tomcat.threads.busy` returns JSON with a `measurements` array.

If 404, Actuator expose didn't take — re-check `application-loadtest.yml` and `SPRING_PROFILES_ACTIVE`.

- [ ] **Step 4: Verify mock worker receives tasks**

```bash
docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml logs worker | tail -10
```

Expected: lines like `celery@... ready.`, `tasks: studio.animate_algorithm`.

- [ ] **Step 5: End-to-end smoke (manual)**

Signup a test user, post animate, observe mock callback:

```bash
curl -s -X POST http://localhost:8080/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"smoke@example.local","password":"LoadTest123!"}' | tee /tmp/smoke_auth.json

TOKEN=$(jq -r .accessToken /tmp/smoke_auth.json)

curl -s -X POST "http://localhost:8080/api/v1/animate?algorithm=bubble-sort" \
  -H "Authorization: Bearer $TOKEN" | tee /tmp/smoke_animate.json

JOB_ID=$(jq -r .jobId /tmp/smoke_animate.json)
echo "job_id=$JOB_ID"

# Poll until SUCCESS (mock sleeps 8–20s)
for i in 1 2 3 4 5 6 7 8; do
  sleep 5
  curl -s "http://localhost:8080/api/v1/animate/status/$JOB_ID" \
    -H "Authorization: Bearer $TOKEN"
  echo
done
```

Expected: status transitions PENDING/RUNNING → SUCCESS within ~30s. If stuck at PENDING, mock worker is not hitting callback — check Step 4 of Task 2 (callback contract).

- [ ] **Step 6: Tear down**

```bash
docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml down
```

Keep the built images. `down -v` would nuke mysql data; not needed here.

- [ ] **Step 7: Commit nothing**

This task is runtime verification — nothing to commit. But if you had to patch the compose override or mock worker in Steps 3–5, commit those fixes separately:

```bash
git status
# If there are diffs:
git add -u && git commit -m "test: fix <what broke> surfaced in smoke test"
```

---

## Task 6: Seed test users

**Files:**
- Create: `loadtest/seed_users.py`
- Create (runtime output, gitignored): `loadtest/tokens.json`

- [ ] **Step 1: Write seed_users.py**

Create `loadtest/seed_users.py`:

```python
"""Create N test accounts via /auth/signup and dump JWTs to tokens.json.

Idempotent: if tokens.json has N entries, exit 0.
"""
import json
import os
import sys
from pathlib import Path
import requests

BACKEND = os.environ.get("LOADTEST_BACKEND", "http://localhost:8080")
PASSWORD = os.environ["LOADTEST_SEED_PASSWORD"]  # required, no default
N_USERS = int(os.environ.get("LOADTEST_N_USERS", "100"))
OUT = Path(__file__).with_name("tokens.json")


def signup(email: str) -> str | None:
    r = requests.post(
        f"{BACKEND}/api/v1/auth/signup",
        json={"email": email, "password": PASSWORD},
        timeout=10,
    )
    if r.status_code == 200 or r.status_code == 201:
        return r.json().get("accessToken")
    # Already registered? Try login.
    r2 = requests.post(
        f"{BACKEND}/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
        timeout=10,
    )
    if r2.status_code == 200:
        return r2.json().get("accessToken")
    print(f"  failed {email}: signup={r.status_code} login={r2.status_code}", file=sys.stderr)
    return None


def main() -> int:
    if OUT.exists():
        existing = json.loads(OUT.read_text())
        if len(existing) >= N_USERS:
            print(f"already have {len(existing)} tokens, skipping")
            return 0

    tokens = []
    for i in range(N_USERS):
        email = f"loadtest+{i}@example.local"
        t = signup(email)
        if t:
            tokens.append({"email": email, "token": t})
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{N_USERS}")

    OUT.write_text(json.dumps(tokens, indent=2))
    print(f"wrote {len(tokens)} tokens to {OUT}")
    return 0 if len(tokens) == N_USERS else 1


if __name__ == "__main__":
    sys.exit(main())
```

**Note on login path:** if `/auth/login` endpoint name differs in this codebase, fix the URL. Check with:
```bash
grep -rn "PostMapping.*login\|@RequestMapping.*login" GIFPT_BE/src/main/java
```

- [ ] **Step 2: Verify accessToken field name**

```bash
grep -n "accessToken\|access_token" GIFPT_BE/src/main/java/com/gifpt/security/auth/controller/AuthController.java | head -5
```

If the JSON key is `access_token` (snake_case) or `token`, fix `seed_users.py` accordingly.

- [ ] **Step 3: Bring the stack back up**

```bash
cd ~/Desktop/GitHub/gifpt/loadtest
docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml up -d
# wait for Spring ready
until curl -sf http://localhost:8080/actuator/health >/dev/null; do sleep 2; done
```

- [ ] **Step 4: Run seeding**

```bash
cd ~/Desktop/GitHub/gifpt/loadtest
python seed_users.py
```

Expected output: `wrote 100 tokens to .../tokens.json`.

- [ ] **Step 5: Verify**

```bash
jq 'length' tokens.json
# 100
jq '.[0].email, .[99].email' tokens.json
# "loadtest+0@example.local"
# "loadtest+99@example.local"
```

- [ ] **Step 6: Commit (script only, never tokens)**

```bash
cd ~/Desktop/GitHub/gifpt
git add -f loadtest/seed_users.py
git status | grep tokens.json && echo "ERROR: tokens.json is staged" && exit 1
git commit -m "test: add user seeding script"
```

---

## Task 7: Metrics collector + environment snapshot

**Files:**
- Create: `loadtest/collect_metrics.sh`
- Create: `loadtest/test-env.md`

- [ ] **Step 1: Write collect_metrics.sh**

Create `loadtest/collect_metrics.sh`:

```bash
#!/usr/bin/env bash
# Usage: ./collect_metrics.sh <output_dir>
# Samples Spring Actuator + MySQL threads every 5s until killed.
set -euo pipefail

OUT="${1:?output dir required}"
mkdir -p "$OUT"
CSV="$OUT/metrics.csv"

ACT=http://localhost:8080/actuator/metrics

metric() {
  curl -s "$ACT/$1" | jq -r '.measurements[] | select(.statistic=="VALUE") | .value' 2>/dev/null || echo ""
}

echo "ts,tomcat_busy,tomcat_current,hikari_active,hikari_pending,hikari_timeout,jvm_mem_used,mysql_threads_connected,mysql_threads_running" > "$CSV"

while true; do
  TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  TB=$(metric tomcat.threads.busy)
  TC=$(metric tomcat.threads.current)
  HA=$(metric hikaricp.connections.active)
  HP=$(metric hikaricp.connections.pending)
  HT=$(metric hikaricp.connections.timeout)
  JM=$(metric jvm.memory.used)

  # MySQL via docker exec
  MYSQL_OUT=$(docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml exec -T mysql \
    mysql -uroot -ploadtest-root -N -e "SHOW STATUS LIKE 'Threads_%'" gifpt 2>/dev/null || echo "")
  MTC=$(echo "$MYSQL_OUT" | awk '$1=="Threads_connected"{print $2}')
  MTR=$(echo "$MYSQL_OUT" | awk '$1=="Threads_running"{print $2}')

  echo "$TS,$TB,$TC,$HA,$HP,$HT,$JM,$MTC,$MTR" >> "$CSV"
  sleep 5
done
```

`chmod +x loadtest/collect_metrics.sh`.

- [ ] **Step 2: Smoke-run the collector for 20s**

In one terminal (stack must be up):
```bash
cd ~/Desktop/GitHub/gifpt/loadtest
mkdir -p results/smoke
./collect_metrics.sh results/smoke &
COLL_PID=$!
sleep 20
kill $COLL_PID
cat results/smoke/metrics.csv
```

Expected: 4–5 rows with numeric values (possibly `""` for hikari.pending if no contention — that's fine).

If every metric column is empty, Actuator names don't match. Check available names:
```bash
curl -s http://localhost:8080/actuator/metrics | jq '.names[]' | grep -iE "tomcat|hikari|jvm"
```

Fix `collect_metrics.sh` metric paths accordingly.

- [ ] **Step 3: Write test-env.md**

Capture the environment now (before any real runs). Create `loadtest/test-env.md`:

```markdown
# Load Test Environment Snapshot

**Run date:** <YYYY-MM-DD>

## Host
- Machine: MacBook M2 <Air/Pro>
- macOS: <version>
- CPU: Apple M2 (<N> cores)
- RAM: <N> GB
- Docker Desktop: <version>

Populate with:
```bash
sw_vers
sysctl -n machdep.cpu.brand_string
sysctl -n hw.memsize | awk '{print $1/1024/1024/1024 " GB"}'
docker version --format '{{.Server.Version}}'
```

## Images (linux/arm64)
- spring: built locally from `GIFPT_BE/Dockerfile`
- django: built locally from `GIFPT_AI/Dockerfile`
- worker: built locally from `loadtest/mock-worker/Dockerfile`, concurrency=4
- mysql: mysql:8.0
- redis: redis:7
- nginx: nginx:1.27-alpine

## Spring
- Java 17 (toolchain)
- Spring Boot 3.5.7
- Profile: `loadtest`
- Actuator exposure: `health, metrics`
- Hikari default max pool size: 10 (override to record actual value)
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
- Version: `k6 version`
- Install: brew

## Caveats
- No Rosetta emulation (arm64 builds), but M2 performance is not EC2 performance.
- Single-host noise: k6 + all services + macOS on one machine. Document mid-run CPU via `top -l 1`.
- This is NOT a prod-accurate absolute threshold. Values are internally consistent for comparing experiments; apply judgment when extrapolating.
```

Fill in the placeholders (`<YYYY-MM-DD>`, `<Air/Pro>`, `<version>`, pool sizes) using the commands shown. These are actual values, not placeholders to leave for later.

- [ ] **Step 4: Commit**

```bash
cd ~/Desktop/GitHub/gifpt
git add -f loadtest/collect_metrics.sh loadtest/test-env.md
git commit -m "test: add metrics collector and environment snapshot"
```

---

## Task 8: k6 Phase 1 script (status-only)

**Files:**
- Create: `loadtest/k6_status_only.js`

- [ ] **Step 1: Write k6 script**

Create `loadtest/k6_status_only.js`:

```javascript
import http from 'k6/http';
import { check } from 'k6';

const BACKEND = __ENV.LOADTEST_BACKEND || 'http://localhost:8080';
// Phase 1: shared token (first seeded user)
const TOKEN = __ENV.LOADTEST_TOKEN;  // required
const FAKE_JOB_ID = __ENV.LOADTEST_FAKE_JOB_ID || '999999999';

if (!TOKEN) throw new Error('LOADTEST_TOKEN env var required');

export const options = {
  stages: [
    { duration: '2m',  target: 50 },   // warmup
    { duration: '3m',  target: 50 },
    { duration: '30s', target: 100 },
    { duration: '3m',  target: 100 },
    { duration: '30s', target: 200 },
    { duration: '3m',  target: 200 },
    { duration: '30s', target: 400 },
    { duration: '3m',  target: 400 },
    { duration: '30s', target: 800 },
    { duration: '3m',  target: 800 },
    { duration: '1m',  target: 0 },
  ],
  thresholds: {
    // 404 is expected (fake jobId) — not a failure for this test
    'http_req_failed{expected_response:true}': ['rate<0.05'],
    'http_req_duration': ['p(95)<2000'],
  },
};

export default function () {
  const res = http.get(
    `${BACKEND}/api/v1/animate/status/${FAKE_JOB_ID}`,
    {
      headers: { Authorization: `Bearer ${TOKEN}` },
      tags: { endpoint: 'status' },
    }
  );
  // 404 is the expected response for a nonexistent jobId
  check(res, {
    'status is 404 or 403': (r) => r.status === 404 || r.status === 403,
  });
}

export function handleSummary(data) {
  return {
    stdout: JSON.stringify(data.metrics.http_req_duration.values, null, 2),
    [`${__ENV.LOADTEST_OUT || '.'}/k6_summary.json`]: JSON.stringify(data, null, 2),
  };
}
```

**Important:** this exercises the full Spring request path (JwtAuthFilter → SecurityContext → controller → JPA `findById`), even though the jobId is fake. The 404 is produced after DB miss, so DB I/O load is realistic.

- [ ] **Step 2: Syntax check**

```bash
cd ~/Desktop/GitHub/gifpt/loadtest
k6 inspect k6_status_only.js
```

Expected: prints stages + thresholds, no parse error.

- [ ] **Step 3: Tiny smoke run (10 VU, 30 seconds)**

Override stages briefly:
```bash
export LOADTEST_TOKEN=$(jq -r '.[0].token' tokens.json)
k6 run --vus 10 --duration 30s --no-summary k6_status_only.js
```

Expected: summary prints; `http_reqs` > 100; no k6 errors. (Ignore threshold breaches for this smoke.)

- [ ] **Step 4: Commit**

```bash
cd ~/Desktop/GitHub/gifpt
git add -f loadtest/k6_status_only.js
git commit -m "test: k6 Phase 1 script for status endpoint"
```

---

## Task 9: k6 Phase 2 script (full flow)

**Files:**
- Create: `loadtest/k6_full_flow.js`

- [ ] **Step 1: Write k6 script**

Create `loadtest/k6_full_flow.js`:

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';
import { SharedArray } from 'k6/data';

const BACKEND = __ENV.LOADTEST_BACKEND || 'http://localhost:8080';
const POLL_INTERVAL_MS = parseInt(__ENV.POLL_INTERVAL_MS || '3000', 10);
const POLL_MAX = parseInt(__ENV.POLL_MAX || '20', 10);
const ALGORITHM_BASE = __ENV.ALGORITHM || 'bubble-sort';

const tokens = new SharedArray('tokens', () =>
  JSON.parse(open('./tokens.json')).map((e) => e.token)
);

export const options = {
  stages: [
    { duration: '2m',  target: 100 },  // warmup
    { duration: '5m',  target: 100 },
    { duration: '30s', target: 200 },
    { duration: '5m',  target: 200 },
    { duration: '30s', target: 400 },
    { duration: '5m',  target: 400 },
    { duration: '30s', target: 800 },
    { duration: '5m',  target: 800 },
    { duration: '2m',  target: 0 },
  ],
  thresholds: {
    'http_req_failed{expected_response:true}': ['rate<0.05'],
    'http_req_duration{endpoint:status}': ['p(95)<2000'],
  },
};

export default function () {
  const token = tokens[Math.floor(Math.random() * tokens.length)];
  const headers = { Authorization: `Bearer ${token}` };

  // Force cache MISS: salt algorithm slug with VU + iteration.
  const slug = `${ALGORITHM_BASE}-${__VU}-${__ITER}`;
  const startRes = http.post(
    `${BACKEND}/api/v1/animate?algorithm=${slug}`,
    null,
    { headers, tags: { endpoint: 'animate' } }
  );

  if (startRes.status !== 202) {
    // Could be 200 cache HIT or error. Either way, skip polling.
    sleep(1);
    return;
  }

  let jobId;
  try { jobId = startRes.json('jobId'); } catch (e) { sleep(1); return; }
  if (!jobId) { sleep(1); return; }

  for (let i = 0; i < POLL_MAX; i++) {
    sleep(POLL_INTERVAL_MS / 1000);
    const r = http.get(
      `${BACKEND}/api/v1/animate/status/${jobId}`,
      { headers, tags: { endpoint: 'status' } }
    );
    check(r, { 'poll ok': (rr) => rr.status < 500 });
    if (r.status === 200) {
      const status = r.json('status');
      if (status === 'SUCCESS' || status === 'FAILED') break;
    }
  }
  sleep(1);
}

export function handleSummary(data) {
  return {
    [`${__ENV.LOADTEST_OUT || '.'}/k6_summary.json`]: JSON.stringify(data, null, 2),
    stdout: JSON.stringify({
      http_req_duration_p95: data.metrics.http_req_duration.values['p(95)'],
      http_reqs: data.metrics.http_reqs.values.count,
      iterations: data.metrics.iterations.values.count,
    }, null, 2),
  };
}
```

- [ ] **Step 2: Syntax check**

```bash
k6 inspect k6_full_flow.js
```

- [ ] **Step 3: Tiny smoke run (5 VU, 90 seconds)**

```bash
cd ~/Desktop/GitHub/gifpt/loadtest
k6 run --vus 5 --duration 90s k6_full_flow.js
```

Expected:
- ~5 jobs dispatched, most reaching SUCCESS (mock sleeps 8–20s, so 90s accommodates 3–4 polls per job)
- Check Spring logs for callback receipt
- `docker compose logs worker | tail -5` shows mock task completions

If polling never resolves, callback is not wiring jobs to SUCCESS — revisit Task 2 Steps 3–4.

- [ ] **Step 4: Commit**

```bash
cd ~/Desktop/GitHub/gifpt
git add -f loadtest/k6_full_flow.js
git commit -m "test: k6 Phase 2 script for full flow"
```

---

## Task 10: Orchestrator script

**Files:**
- Create: `loadtest/run_experiment.sh`

- [ ] **Step 1: Write orchestrator**

Create `loadtest/run_experiment.sh`:

```bash
#!/usr/bin/env bash
# Usage: ./run_experiment.sh <experiment> <phase> [run_number]
#   experiment: baseline | redis_cache | interval_1s
#   phase:      phase1 | phase2
#   run_number: 1–3 (default 1)
#
# Starts metrics collector, runs k6, stops collector, writes summary.
set -euo pipefail

EXP="${1:?experiment required}"
PHASE="${2:?phase required}"
RUN="${3:-1}"

TS=$(date -u +%Y%m%d-%H%M%S)
OUT="results/${EXP}/${PHASE}/run${RUN}-${TS}"
mkdir -p "$OUT"

echo "=== $EXP / $PHASE / run $RUN → $OUT ==="

# Pre-flight
if ! curl -sf http://localhost:8080/actuator/health >/dev/null; then
  echo "Spring not healthy. Aborting."
  exit 1
fi

# Start collector
./collect_metrics.sh "$OUT" &
COLL_PID=$!
trap 'kill $COLL_PID 2>/dev/null || true' EXIT

# Pick script and env
case "$PHASE" in
  phase1)
    export LOADTEST_TOKEN=$(jq -r '.[0].token' tokens.json)
    SCRIPT=k6_status_only.js
    ;;
  phase2)
    SCRIPT=k6_full_flow.js
    ;;
  *) echo "unknown phase"; exit 1 ;;
esac

# Experiment-specific overrides
case "$EXP" in
  interval_1s)
    export POLL_INTERVAL_MS=1000
    ;;
  baseline|redis_cache)
    export POLL_INTERVAL_MS=3000
    ;;
esac

export LOADTEST_OUT="$OUT"

# Run k6
k6 run "$SCRIPT" | tee "$OUT/k6_stdout.txt"

kill $COLL_PID 2>/dev/null || true

# Capture actuator snapshot at end-of-run
curl -s http://localhost:8080/actuator/metrics \
  | jq '.names' > "$OUT/actuator_names.json"

# Write summary stub
cat > "$OUT/summary.md" <<EOF
# Run summary: $EXP / $PHASE / run $RUN

**Timestamp:** $TS
**Script:** $SCRIPT
**Overrides:** POLL_INTERVAL_MS=$POLL_INTERVAL_MS

## k6 output
See \`k6_summary.json\`, \`k6_stdout.txt\`.

## Metrics
See \`metrics.csv\`.

## Observations
<!-- fill after reviewing -->

EOF

echo "=== done → $OUT ==="
```

`chmod +x loadtest/run_experiment.sh`.

- [ ] **Step 2: Verify syntax**

```bash
bash -n loadtest/run_experiment.sh
```

Expected: no output (clean).

- [ ] **Step 3: Commit**

```bash
cd ~/Desktop/GitHub/gifpt
git add -f loadtest/run_experiment.sh
git commit -m "test: orchestrator script for experiment runs"
```

---

## Task 11: Run Baseline (Phase 1 + Phase 2, 3 reps each)

**Files:** no code. Outputs under `loadtest/results/baseline/`.

This task takes **~3 hours real time** (Phase 1 is ~19 min × 3 = ~1h, Phase 2 is ~25 min × 3 = ~1h 15m, plus restarts).

- [ ] **Step 1: Bring stack up clean**

```bash
cd ~/Desktop/GitHub/gifpt/loadtest
docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml down
docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml up -d
until curl -sf http://localhost:8080/actuator/health >/dev/null; do sleep 2; done
python seed_users.py  # idempotent
```

- [ ] **Step 2: Phase 1 × 3**

```bash
./run_experiment.sh baseline phase1 1
docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml restart spring mysql
sleep 15
./run_experiment.sh baseline phase1 2
docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml restart spring mysql
sleep 15
./run_experiment.sh baseline phase1 3
```

Between runs: restart Spring + MySQL (not Redis, since no cache in baseline) to reset JVM JIT state and connection pool. Wait 15s for services to re-stabilize.

- [ ] **Step 3: Phase 2 × 3**

```bash
docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml restart spring mysql
sleep 15
./run_experiment.sh baseline phase2 1
docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml restart spring mysql
sleep 15
./run_experiment.sh baseline phase2 2
docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml restart spring mysql
sleep 15
./run_experiment.sh baseline phase2 3
```

- [ ] **Step 4: Validate each run**

For each of the 6 result directories:
```bash
for d in results/baseline/phase*/run*-*; do
  echo "=== $d ==="
  jq '.metrics.http_req_duration.values."p(95)"' "$d/k6_summary.json"
  wc -l "$d/metrics.csv"
done
```

Expected: every `k6_summary.json` exists and has a p(95) number; every `metrics.csv` has >50 rows.

If a run is clearly invalid (e.g., machine paused, CPU pegged from another app, k6 crashed), delete the run directory and redo it. Note this in the run's `summary.md` BEFORE deleting.

- [ ] **Step 5: Fill in summary.md for each run**

For each run, open `summary.md` and write 3–5 bullet observations:
- Top-level k6 numbers (p50/p95/reqs/errors)
- Metrics.csv anomalies (thread pool saturation? pending connections?)
- Any host-side noise (macOS doing a Spotlight index, other apps)

Do not interpret yet. Just note.

- [ ] **Step 6: Commit summaries**

```bash
cd ~/Desktop/GitHub/gifpt
git add -f loadtest/results/baseline/*/*/summary.md
git commit -m "test: capture baseline Phase 1 + Phase 2 run summaries"
```

Raw JSON/CSV stay gitignored.

---

## Task 12: Run Experiment C (Phase 2 with 1s interval, 3 reps)

**Files:** no code. Outputs under `loadtest/results/interval_1s/phase2/`.

- [ ] **Step 1: Restart stack**

```bash
cd ~/Desktop/GitHub/gifpt/loadtest
docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml restart spring mysql
sleep 15
```

- [ ] **Step 2: Phase 2 × 3 with interval 1s**

```bash
./run_experiment.sh interval_1s phase2 1
docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml restart spring mysql
sleep 15
./run_experiment.sh interval_1s phase2 2
docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml restart spring mysql
sleep 15
./run_experiment.sh interval_1s phase2 3
```

- [ ] **Step 3: Validate + fill summary.md**

Same as Task 11 Steps 4–5.

- [ ] **Step 4: Commit**

```bash
cd ~/Desktop/GitHub/gifpt
git add -f loadtest/results/interval_1s/phase2/*/summary.md
git commit -m "test: capture interval_1s Phase 2 run summaries"
```

---

## Task 13: Experiment B — Redis cache patch and runs

**Files (all on throwaway branch `experiment-b/redis-status-cache`):**
- Modify: `GIFPT_BE/build.gradle`
- Modify: `GIFPT_BE/src/main/resources/application-loadtest.yml`
- Create: `GIFPT_BE/src/main/java/com/gifpt/analysis/cache/StatusCache.java`
- Modify: `GIFPT_BE/src/main/java/com/gifpt/analysis/controller/AnimateController.java`

- [ ] **Step 1: Branch from current loadtest branch**

```bash
cd ~/Desktop/GitHub/gifpt
git checkout -b experiment-b/redis-status-cache
```

- [ ] **Step 2: Add Redis dependency**

Edit `GIFPT_BE/build.gradle`, add in `dependencies { ... }`:

```gradle
	implementation 'org.springframework.boot:spring-boot-starter-data-redis'
```

- [ ] **Step 3: Add Redis config to loadtest profile**

Edit `GIFPT_BE/src/main/resources/application-loadtest.yml`, append:

```yaml
spring:
  data:
    redis:
      host: ${REDIS_HOST:redis}
      port: 6379
```

Merge into existing `spring:` block (don't create a second `spring:` key).

- [ ] **Step 4: Write StatusCache.java**

Create `GIFPT_BE/src/main/java/com/gifpt/analysis/cache/StatusCache.java`:

```java
package com.gifpt.analysis.cache;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.Map;

@Component
public class StatusCache {
    private static final Duration TTL = Duration.ofSeconds(2);
    private static final String KEY_PREFIX = "gifpt:status:";

    @Autowired private StringRedisTemplate redis;
    @Autowired private ObjectMapper mapper;

    public Map<String, Object> get(long jobId) {
        String json = redis.opsForValue().get(KEY_PREFIX + jobId);
        if (json == null) return null;
        try {
            return mapper.readValue(json, Map.class);
        } catch (Exception e) {
            return null;
        }
    }

    public void put(long jobId, Map<String, Object> value) {
        try {
            redis.opsForValue().set(KEY_PREFIX + jobId, mapper.writeValueAsString(value), TTL);
        } catch (Exception e) {
            // Fail open: cache write errors must not poison the request path.
        }
    }
}
```

- [ ] **Step 5: Modify AnimateController.getStatus to use cache**

Edit `GIFPT_BE/src/main/java/com/gifpt/analysis/controller/AnimateController.java`:

Inject the cache:
```java
    @Autowired private com.gifpt.analysis.cache.StatusCache statusCache;
```

Replace the body of `getStatus` (line 180–199) with:

```java
    @GetMapping("/status/{jobId}")
    public ResponseEntity<?> getStatus(
            @PathVariable Long jobId,
            @AuthenticationPrincipal @Nullable CustomUserPrincipal user
    ) {
        Map<String, Object> cached = statusCache.get(jobId);
        Long ownerId;
        Map<String, Object> response;

        if (cached != null) {
            ownerId = ((Number) cached.get("userId")).longValue();
            response = Map.of(
                    "jobId", cached.get("jobId"),
                    "status", cached.get("status"),
                    "resultUrl", cached.get("resultUrl"),
                    "errorMessage", cached.get("errorMessage")
            );
        } else {
            AnalysisJob job = analysisJobRepository.findById(jobId)
                    .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Job not found"));
            ownerId = job.getUserId();
            response = Map.of(
                    "jobId", job.getId(),
                    "status", job.getStatus().name(),
                    "resultUrl", job.getResultUrl() != null ? job.getResultUrl() : "",
                    "errorMessage", job.getErrorMessage() != null ? job.getErrorMessage() : ""
            );
            Map<String, Object> cacheValue = new java.util.HashMap<>(response);
            cacheValue.put("userId", ownerId);
            statusCache.put(jobId, cacheValue);
        }

        if (user == null || !ownerId.equals(user.getId())) {
            return ResponseEntity.status(HttpStatus.FORBIDDEN)
                    .body(Map.of("error", "forbidden"));
        }

        return ResponseEntity.ok(response);
    }
```

**Auth note:** cache stores `userId`; auth check runs after cache lookup using the cached `userId`. No user data leaks across accounts because the cache key is `jobId` (job-specific) and the auth check still compares against the requester.

- [ ] **Step 6: Build**

```bash
cd ~/Desktop/GitHub/gifpt/GIFPT_BE
./gradlew build -x test --quiet 2>&1 | tail -3
```

Expected: `BUILD SUCCESSFUL`.

- [ ] **Step 7: Rebuild Spring image and restart**

```bash
cd ~/Desktop/GitHub/gifpt/loadtest
docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml build spring
docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml up -d
until curl -sf http://localhost:8080/actuator/health >/dev/null; do sleep 2; done
```

- [ ] **Step 8: Smoke verify cache**

Fire two identical status requests and confirm the second is faster (or at least doesn't increment DB query count).

```bash
# Prime: signup + animate + get a real jobId
curl -s -X POST http://localhost:8080/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"b-smoke@example.local","password":"LoadTest123!"}' > /tmp/b.json
TOKEN=$(jq -r .accessToken /tmp/b.json)
curl -s -X POST "http://localhost:8080/api/v1/animate?algorithm=bubble-smoke" \
  -H "Authorization: Bearer $TOKEN" > /tmp/ba.json
JOB_ID=$(jq -r .jobId /tmp/ba.json)

# Two back-to-back status calls
time curl -s "http://localhost:8080/api/v1/animate/status/$JOB_ID" -H "Authorization: Bearer $TOKEN" >/dev/null
time curl -s "http://localhost:8080/api/v1/animate/status/$JOB_ID" -H "Authorization: Bearer $TOKEN" >/dev/null

# Verify Redis has the key
docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml exec -T redis \
  redis-cli GET "gifpt:status:$JOB_ID"
```

Expected: Redis GET returns a JSON string, not `(nil)`. Second `time` output is noticeably faster (typically <5ms vs 20–50ms).

- [ ] **Step 9: Run Phase 1 × 3**

```bash
./run_experiment.sh redis_cache phase1 1
docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml restart spring mysql redis
sleep 15
./run_experiment.sh redis_cache phase1 2
docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml restart spring mysql redis
sleep 15
./run_experiment.sh redis_cache phase1 3
```

- [ ] **Step 10: Run Phase 2 × 3**

```bash
docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml restart spring mysql redis
sleep 15
./run_experiment.sh redis_cache phase2 1
docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml restart spring mysql redis
sleep 15
./run_experiment.sh redis_cache phase2 2
docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml restart spring mysql redis
sleep 15
./run_experiment.sh redis_cache phase2 3
```

- [ ] **Step 11: Fill summaries**

Same as Task 11 Step 5.

- [ ] **Step 12: Commit results on the throwaway branch**

```bash
cd ~/Desktop/GitHub/gifpt
git add GIFPT_BE/build.gradle \
        GIFPT_BE/src/main/resources/application-loadtest.yml \
        GIFPT_BE/src/main/java/com/gifpt/analysis/cache/StatusCache.java \
        GIFPT_BE/src/main/java/com/gifpt/analysis/controller/AnimateController.java
git commit -m "test(exp-b): Redis status cache for loadtest measurement only"

git add -f loadtest/results/redis_cache/*/*/summary.md
git commit -m "test(exp-b): capture redis_cache run summaries"
```

- [ ] **Step 13: Switch back, preserve the branch**

```bash
git checkout docs/polling-loadtest-spec
git branch --list experiment-b/redis-status-cache
# Branch remains for reference. Do NOT merge to any other branch.
```

- [ ] **Step 14: Copy summaries to the main loadtest branch**

The summary files in `loadtest/results/redis_cache/...` are gitignored raw outputs on experiment-b branch, but their `summary.md` siblings were force-added there. Cherry-pick those commits to this branch so RESULTS.md (next task) can reference them from one place.

```bash
git log --oneline experiment-b/redis-status-cache ^HEAD | head
git cherry-pick <summary commit SHA>
```

If the cherry-pick conflicts on Spring source files (because the cache patch also landed on experiment-b), drop the Spring files during cherry-pick:
```bash
git cherry-pick --strategy-option=theirs <SHA>  # or manually:
git checkout --ours GIFPT_BE/
git add GIFPT_BE/
git cherry-pick --continue
```

Goal: `loadtest/results/redis_cache/**/summary.md` exists on `docs/polling-loadtest-spec`, Spring source does NOT.

---

## Task 14: Aggregate into RESULTS.md

**Files:**
- Create: `loadtest/RESULTS.md`

- [ ] **Step 1: Build the numbers table**

Use `jq` to extract p50/p95/error/rps from every `k6_summary.json` in `results/`:

```bash
cd ~/Desktop/GitHub/gifpt/loadtest
for d in results/*/*/run*-*; do
  if [ -f "$d/k6_summary.json" ]; then
    printf "%s\t" "$d"
    jq -r '[.metrics.http_req_duration.values."p(50)",
            .metrics.http_req_duration.values."p(95)",
            .metrics.http_req_failed.values.rate,
            .metrics.http_reqs.values.rate] | @tsv' "$d/k6_summary.json"
  fi
done | column -t
```

Note: some `k6_summary.json` may need to gitignore-exempt on this branch if they didn't survive the cherry-pick. If missing, extract from the `summary.md` if you captured numbers there.

- [ ] **Step 2: Write RESULTS.md**

Create `loadtest/RESULTS.md` following this template:

```markdown
# gifpt Polling Load Test — Results

**Test dates:** <start> to <end>
**Spec:** `docs/superpowers/specs/2026-04-21-gifpt-polling-loadtest-design.md`
**Environment:** see `test-env.md`

## Summary table (median across 3 runs)

### Phase 1 — status endpoint only

| Experiment | VU | p50 (ms) | p95 (ms) | error rate | RPS |
|---|---|---|---|---|---|
| Baseline      |  50 | ... | ... | ... | ... |
| Baseline      | 100 | ... | ... | ... | ... |
| Baseline      | 200 | ... | ... | ... | ... |
| Baseline      | 400 | ... | ... | ... | ... |
| Baseline      | 800 | ... | ... | ... | ... |
| Redis cache   |  50 | ... | ... | ... | ... |
| ...           | ... | ... | ... | ... | ... |

### Phase 2 — full flow

| Experiment | VU | p50 (ms) | p95 (ms) | error rate | RPS |
|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... |

## Curve shape observations

### Baseline
- <describe: is the curve linear or exponential? at what VU does error rate climb?>

### Redis cache
- <delta vs baseline at each VU level>

### Interval 1s
- <how does system behave with 3× polling rate>

## Bottleneck identification

From `metrics.csv` at the highest-VU stage:
- Tomcat `threads.busy` peaked at <N> / <max>
- Hikari `connections.active` peaked at <N> / <max>; `connections.pending` reached <N>
- MySQL `Threads_running` peaked at <N>
- JVM memory growth: <flat | sawtooth | runaway>

**Where is the bottleneck?** <Tomcat | Hikari | MySQL | GC | none reached at 800 VU>

## Answers to spec's judgment criteria

1. **Is the p95 curve linear up to VU 400?**
   <yes/no + evidence>

2. **Where is the bottleneck?**
   <layer>

3. **Does Redis cache reduce p95 by 40%+?**
   <delta + verdict>

4. **Is interval 1s safe?**
   <verdict>

## Recommendation

<one of:>
- **Keep polling as-is** — <rationale>
- **Polling + Redis cache** — <rationale; this is the "middle option" mentioned in the spec>
- **Migrate to SSE** — <rationale; what specifically breaks at what scale>
- **Polling + interval 1s + Redis cache** — <rationale>

## Caveats

- MacBook M2, not EC2. Absolute thresholds do not transfer.
- Mock worker concurrency=4, not prod-representative for worker layer.
- Cache-MISS salting was `${ALGORITHM_BASE}-${__VU}-${__ITER}`, which does not reflect the cache-HIT/MISS ratio the real service would see post-launch.
- <any measurement-invalid runs and what we did about them>

## Next steps

- If recommendation requires Spring changes: open a fresh branch from `main` (not from experiment-b), reimplement cleanly with tests.
- OpenAI key structure rework is still pending — see spec Non-goals.
```

Fill in every `...` with actual numbers. No TODOs.

- [ ] **Step 3: Commit RESULTS.md**

```bash
cd ~/Desktop/GitHub/gifpt
git add -f loadtest/RESULTS.md
git commit -m "test: aggregate loadtest results and recommendation"
```

- [ ] **Step 4: Surface to user**

Print the recommendation section and the summary table to the terminal and ask the user to review. This is the artifact the whole campaign existed to produce.

---

## Post-plan: Execution handoff

Plan complete. After execution, the `docs/polling-loadtest-spec` branch will contain:
- Spec (committed in brainstorming step)
- loadtest infrastructure (Tasks 1–10)
- Run summaries (Tasks 11, 12; plus Task 13 cherry-picks)
- RESULTS.md with recommendation (Task 14)

The `experiment-b/redis-status-cache` branch will exist as a throwaway reference but will NOT be merged.

If the recommendation from Task 14 is "make a Spring change", a clean new branch from `main` should do that work with its own TDD and tests — not this branch.
