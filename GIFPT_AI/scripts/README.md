# Audit scripts — weekly review routine

Three scripts that turn the GIFPT pipeline's runtime signal into one markdown
file you read for ~5 minutes each week. Final review/judgment is yours; the
scripts only collect and summarize.

## What's here

| Script | Reads from | Writes to | Cost | Run cadence |
|---|---|---|---|---|
| `failure_audit.py` | MySQL `analysis_jobs` (Spring backend) | `reports/failure_audit_YYYY-MM-DD.{json,md}` | free | weekly |
| `seed_audit.py` | `studio/ai/examples/seed_examples.jsonl` | `reports/seed_audit_YYYY-MM-DD.{json,md}` | ~$0.50 + 10–15 min | weekly or on-demand |
| `weekly_audit.py` | runs both above | `reports/weekly_YYYY-MM-DD.md` | sum of above | weekly (the only command you actually type) |

`reports/` is gitignored — these are working notes, not artifacts.

## One-time setup

```bash
cd GIFPT_AI

# 1. install the optional MySQL driver used by failure_audit
pip install pymysql

# 2. set DB credentials (matches GIFPT_BE/src/main/resources/application-local.yml)
export GIFPT_MYSQL_HOST=127.0.0.1
export GIFPT_MYSQL_USER=root
export GIFPT_MYSQL_PASSWORD='your_local_mysql_password'
export GIFPT_MYSQL_DB=gifpt

# 3. seed_audit needs the same env that the Celery worker uses
export OPENAI_API_KEY=sk-...
# (manim must be importable — already in requirements.txt)
```

Stash the env vars in your shell rc or a `.envrc` so you don't re-export weekly.
Never commit real secrets to the repository.

## The weekly routine

Once a week (e.g. Monday morning):

```bash
cd GIFPT_AI
python -m scripts.weekly_audit
open reports/weekly_$(date -u +%Y-%m-%d).md
```

Read the file top-to-bottom. It is structured for 5-minute scanning:

1. **Failure section**
   - Look at the **stage table** first — has any stage's share jumped vs last week?
   - Look at the **domain table** — any row with a `!` flag (≥30% fail rate, ≥3 jobs) is the week's investigation target.
   - Skim **top failing slugs** — repeated identical errors usually point to one missing prompt rule or one broken seed example.

2. **Seed section**
   - Any `FAIL` in the render or QA column means a few-shot example is now degrading every prompt that pulls it. Highest-leverage fix.
   - Schema issues are usually trivial — fix in the JSONL directly.

3. **Action items** (bottom of each section)
   - Write 1–3 items in the checkboxes. If you can't think of any, the week was healthy — close the file.
   - These items become next week's tickets / commits.

If the full run is too slow on a given week, use:

```bash
python -m scripts.weekly_audit --seed-no-qa     # render seeds, skip $0.50 of OpenAI calls
python -m scripts.weekly_audit --seed-dry-run   # schema check only — completes in <1s
python -m scripts.weekly_audit --skip-seed      # failure_audit only
```

## When to run individual scripts

- **Just shipped a prompt change to `llm_codegen.py`** → `python -m scripts.seed_audit` to confirm none of the canonical examples regressed.
- **Investigating a specific seed** → `python -m scripts.seed_audit --tag bubble_sort`.
- **Ad-hoc failure check** → `python -m scripts.failure_audit --days 1`.
- **No DB access (e.g. on a plane)** → export the table first, then  
  `python -m scripts.failure_audit --source json /tmp/jobs_dump.json`. The dump should be a JSON array of records with at least `algorithm_slug`, `status`, `error_message`, `created_at`.

## Stage classification (failure_audit)

The Spring `analysis_jobs` table only stores `errorMessage` as free text — there's
no explicit "stage" column. `failure_audit.py` regex-classifies messages into:

- `ir_validation` — IR validators in `studio/ai/qa.py`
- `codegen` — `validate_manim_code_basic` static checks
- `render` / `render_timeout` — `ManimRenderError` from `run_manim_code`
- `qa` — vision QA below threshold
- `callback` — Django → Spring callback failures
- `unknown` — anything that didn't match (review these; if a category recurs, add a regex)

The patterns live in `STAGE_PATTERNS` at the top of `failure_audit.py`. When you
see a recurring `Unknown` row in the report, edit those patterns — that's the
maintenance cost of this script.

## What this is NOT

- **Not a benchmark suite.** Baseline / ablation scripts come later, after the
  weekly routine has been running long enough to see real-world variance.
- **Not a substitute for QA validation.** Vision QA scores in seed_audit are
  only trustworthy after you've calibrated the QA system against ~30 hand-labeled
  examples (the "Day 2" task in the broader plan).
- **Not a CI gate.** These run locally. CI regression tests are a separate piece
  of work that will eventually consume the same `seed_audit.py` machinery.
