#!/usr/bin/env bash
# Usage: ./collect_metrics.sh <output_dir>
# Samples Spring Actuator + MySQL threads every 5s until killed.
set -euo pipefail

OUT="${1:?output dir required}"
mkdir -p "$OUT"
CSV="$OUT/metrics.csv"

ACT=http://localhost:8080/actuator/metrics

# Take the first matching measurement only — multi-dimension metrics return
# multiple rows and would otherwise produce a multi-line CSV cell.
metric_stat() {
  curl -s "$ACT/$1" \
    | jq -r --arg s "$2" '[.measurements[]? | select(.statistic==$s) | .value][0] // empty' \
      2>/dev/null || echo ""
}

metric_value()  { metric_stat "$1" VALUE; }
metric_active() { metric_stat "$1" ACTIVE_TASKS; }
metric_count()  { metric_stat "$1" COUNT; }
metric_sum()    { metric_stat "$1" TOTAL_TIME; }
metric_max()    { metric_stat "$1" MAX; }

echo "ts,http_active,jvm_threads_live,hikari_active,hikari_pending,hikari_timeout_count,gc_pause_total_s,gc_pause_max_s,jvm_mem_used,mysql_threads_connected,mysql_threads_running" > "$CSV"

while true; do
  TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  HA=$(metric_active http.server.requests.active)
  JTL=$(metric_value jvm.threads.live)
  HKA=$(metric_value hikaricp.connections.active)
  HKP=$(metric_value hikaricp.connections.pending)
  HKT=$(metric_count hikaricp.connections.timeout)
  GCP_TOTAL=$(metric_sum jvm.gc.pause)
  GCP_MAX=$(metric_max jvm.gc.pause)
  JM=$(metric_value jvm.memory.used)

  MYSQL_OUT=$(docker compose -f ../docker-compose.yml -f docker-compose.loadtest.yml exec -T mysql \
    mysql -uroot -ploadtest-root -N -e "SHOW STATUS LIKE 'Threads_%'" gifpt 2>/dev/null || echo "")
  MTC=$(echo "$MYSQL_OUT" | awk '$1=="Threads_connected"{print $2}')
  MTR=$(echo "$MYSQL_OUT" | awk '$1=="Threads_running"{print $2}')

  echo "$TS,$HA,$JTL,$HKA,$HKP,$HKT,$GCP_TOTAL,$GCP_MAX,$JM,$MTC,$MTR" >> "$CSV"
  sleep 5
done
