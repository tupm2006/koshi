#!/usr/bin/env bash
# Operational snapshot of a running Koshi instance.
#
#   ./scripts/monitor.sh                       # localhost:8090, once
#   ./scripts/monitor.sh https://koshi.huynhca.com
#   WATCH=60 ./scripts/monitor.sh              # repeat every 60 s
#
# Reads METRICS_TOKEN from the environment (never from a file argument), so the
# token does not land in shell history or a process list.
set -euo pipefail

BASE="${1:-http://localhost:8090}"
BASE="${BASE%/}"

snapshot() {
  echo "== $(date '+%F %T')  $BASE"

  health=$(curl -s -o /dev/null -w '%{http_code} %{time_total}' "$BASE/api/health" || echo "000 0")
  echo "health      HTTP ${health% *}  (${health#* }s)"

  if command -v docker >/dev/null; then
    docker ps --filter name=koshi --format '{{.Names}}\t{{.Status}}' | sed 's/^/container   /'
  fi

  if [ -n "${METRICS_TOKEN:-}" ]; then
    m=$(curl -s -H "Authorization: Bearer $METRICS_TOKEN" "$BASE/api/metrics" || true)
    if [ -n "$m" ]; then
      echo "$m" | awk '
        /^koshi_uptime_seconds/ { printf "uptime      %dh%02dm\n", $2/3600, ($2%3600)/60 }
        /^koshi_http_requests_total/ { total += $2; if ($0 ~ /status="5/) err += $2 }
        /^koshi_ai_answers_total/ { ai += $2; if ($0 ~ /tier="fallback"/) fb += $2 }
        END {
          printf "requests    %d total, %d server errors\n", total, err
          if (ai) printf "AI answers  %d, %d from the offline fallback (%.0f%%)\n", ai, fb, 100*fb/ai
          if (ai && fb/ai > 0.5) print "WARNING     most AI answers are fallback — check the provider key/quota"
          if (err > 0) print "WARNING     5xx responses recorded — see: docker logs koshi-backend-prod-local"
        }'
    else
      echo "metrics     unavailable (wrong token?)"
    fi
  else
    echo "metrics     set METRICS_TOKEN to read /api/metrics"
  fi
}

if [ -n "${WATCH:-}" ]; then
  while true; do snapshot; sleep "$WATCH"; done
else
  snapshot
fi
