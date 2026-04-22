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
