#!/usr/bin/env bash
# Usage: ./collect_metrics.sh <output_dir>
# Samples Spring Actuator + MySQL threads every 5s until killed.
set -euo pipefail

OUT="${1:?output dir required}"
mkdir -p "$OUT"
CSV="$OUT/metrics.csv"

ACT=http://localhost:8080/actuator/metrics

metric_value() {
  curl -s "$ACT/$1" | jq -r '.measurements[] | select(.statistic=="VALUE") | .value' 2>/dev/null || echo ""
}

metric_active() {
  curl -s "$ACT/$1" | jq -r '.measurements[] | select(.statistic=="ACTIVE_TASKS") | .value' 2>/dev/null || echo ""
}

metric_count() {
  curl -s "$ACT/$1" | jq -r '.measurements[] | select(.statistic=="COUNT") | .value' 2>/dev/null || echo ""
}

metric_sum() {
  curl -s "$ACT/$1" | jq -r '.measurements[] | select(.statistic=="TOTAL_TIME") | .value' 2>/dev/null || echo ""
}

metric_max() {
  curl -s "$ACT/$1" | jq -r '.measurements[] | select(.statistic=="MAX") | .value' 2>/dev/null || echo ""
}

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
