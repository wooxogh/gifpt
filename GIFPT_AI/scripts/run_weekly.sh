#!/usr/bin/env bash
# run_weekly.sh — automated weekly audit with macOS notification.
#
# Loads secrets from .env.audit, runs weekly_audit, notifies when done.
# Designed to be called from crontab or launchd.
#
# Usage:
#   ./scripts/run_weekly.sh              # full run (failures + seed re-render + QA)
#   ./scripts/run_weekly.sh --fast       # failures + seed schema check only (no $, <5s)
#   ./scripts/run_weekly.sh --no-seed    # failure audit only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GIFPT_AI_DIR="$(dirname "$SCRIPT_DIR")"
REPORTS_DIR="$GIFPT_AI_DIR/reports"

# ── Load env ──────────────────────────────────────────────────────────────────
ENV_FILE="$SCRIPT_DIR/.env.audit"
if [[ ! -f "$ENV_FILE" ]]; then
    echo "[run_weekly] .env.audit not found at $ENV_FILE"
    echo "[run_weekly] Copy .env.audit.example → .env.audit and fill in secrets."
    exit 2
fi
set -a
source "$ENV_FILE"
set +a

PYTHON="${PYTHON:-python3}"

# ── Parse mode ────────────────────────────────────────────────────────────────
AUDIT_ARGS=()
MODE="full"

case "${1:-}" in
    --fast)
        AUDIT_ARGS+=(--seed-dry-run)
        MODE="fast"
        ;;
    --no-seed)
        AUDIT_ARGS+=(--skip-seed)
        MODE="failures-only"
        ;;
    "")
        # full run
        ;;
    *)
        echo "Usage: $0 [--fast|--no-seed]"
        exit 1
        ;;
esac

# ── Capture today's date before the audit runs (handles midnight boundary) ──────
TODAY=$(date '+%Y-%m-%d')
REPORT="$REPORTS_DIR/weekly_${TODAY}.md"

# ── Run ───────────────────────────────────────────────────────────────────────
cd "$GIFPT_AI_DIR"

echo "[run_weekly] mode=$MODE started=$(date '+%Y-%m-%d %H:%M')"
rc=0
if "$PYTHON" -m scripts.weekly_audit "${AUDIT_ARGS[@]}"; then
    STATUS="done"
else
    rc=$?
    STATUS="error (exit $rc)"
fi

# ── macOS notification ────────────────────────────────────────────────────────
if command -v osascript &>/dev/null; then
    if [[ "$STATUS" == "done" && -f "$REPORT" ]]; then
        osascript -e "display notification \"Weekly audit ready — open reports/weekly_${TODAY}.md\" with title \"GIFPT Audit\" sound name \"Glass\""
    else
        osascript -e "display notification \"Weekly audit finished with status: $STATUS\" with title \"GIFPT Audit\" sound name \"Basso\""
    fi
fi

# ── Auto-open if running interactively ────────────────────────────────────────
if [[ -t 1 && -f "$REPORT" ]]; then
    open "$REPORT"
fi

echo "[run_weekly] status=$STATUS report=$REPORT"
exit $rc
