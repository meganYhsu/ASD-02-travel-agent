#!/usr/bin/env bash
set -euo pipefail
umask 077

deployment_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$deployment_dir/reports"
log_file="$deployment_dir/reports/$(date -u +%Y%m%dT%H%M%SZ)-smoke.log"

{
  for endpoint in \
    http://127.0.0.1:8080/ \
    http://127.0.0.1:3001/ \
    http://127.0.0.1:3002/booking \
    http://127.0.0.1:3003/ \
    http://127.0.0.1:3004/ \
    http://127.0.0.1:8505/ \
    http://127.0.0.1:5004/api/saved_itineraries; do
    curl --fail --silent --show-error --output /dev/null \
      --connect-timeout 5 --max-time 15 --retry 12 --retry-delay 5 \
      --retry-connrefused "$endpoint"
    printf 'PASS HTTP response: %s\n' "$endpoint"
  done
  printf 'Reachability checks only; CRUD, database persistence, and AI-disable checks remain required.\n'
} 2>&1 | tee "$log_file"
