# gifpt Polling Layer Load Test

See spec: `docs/superpowers/specs/2026-04-21-gifpt-polling-loadtest-design.md`

## Prereqs
- Docker Desktop running
- k6 (`brew install k6`)
- Python 3.11+ (for seed_users.py)

## Quickstart
~~~bash
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
~~~

## Artifacts
Each run lands in `results/<timestamp>/`. Final aggregation in `RESULTS.md`.
