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
