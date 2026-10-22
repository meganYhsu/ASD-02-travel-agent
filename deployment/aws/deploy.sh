#!/usr/bin/env bash
set -euo pipefail
umask 077

deployment_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repository_dir="$(cd "$deployment_dir/../.." && pwd)"
compose=(docker compose -f "$deployment_dir/compose.yaml")

case "${1:-validate}" in
  validate)
    "${compose[@]}" config --quiet
    "${compose[@]}" config --services
    ;;
  build|start|status|logs|stop)
    mkdir -p "$deployment_dir/reports"
    log_file="$deployment_dir/reports/$(date -u +%Y%m%dT%H%M%SZ)-$1.log"
    {
      printf 'UTC: %s\n' "$(date -u +%FT%TZ)"
      git -C "$repository_dir" rev-parse HEAD
      "${compose[@]}" config --quiet
      case "$1" in
        build) COMPOSE_PARALLEL_LIMIT=1 "${compose[@]}" build ;;
        start) "${compose[@]}" up -d --no-build ;;
        status) "${compose[@]}" ps --all ;;
        logs) "${compose[@]}" logs --no-color --tail 100 ;;
        stop) "${compose[@]}" stop ;;
      esac
    } 2>&1 | tee "$log_file"
    ;;
  *)
    printf 'Usage: bash deployment/aws/deploy.sh {validate|build|start|status|logs|stop}\n' >&2
    exit 2
    ;;
esac
