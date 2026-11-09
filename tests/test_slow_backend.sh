#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$PROJECT_DIR"

BASE_URL="http://127.0.0.1:8088"

check_slow_route_disabled() {
  local status
  status=$(curl -sS --max-time 10 -o /dev/null -w '%{http_code}' \
    "$BASE_URL/lab/slow") || return 1

  if [[ "$status" != 404 ]]; then
    printf '[FAIL] Expected HTTP 404 with the slow route disabled, got %s\n' \
      "$status" >&2
    return 1
  fi

  echo "[ OK ] Slow route disabled (HTTP 404)"
}

restore_default() {
  local status=$?
  trap - EXIT
  echo "Restoring the default Compose configuration..."

  if docker compose up -d --wait --wait-timeout 60 &&
     check_slow_route_disabled; then
    echo "[ OK ] Default configuration restored"
  else
    echo "[FAIL] Could not restore or verify the default configuration" >&2
    status=1
  fi

  exit "$status"
}

docker compose up -d --build --wait --wait-timeout 60
check_slow_route_disabled

trap restore_default EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

docker compose -f compose.yaml -f compose.slow.yaml \
  up -d --wait --wait-timeout 60

python3 scripts/probe_slow_backend.py
curl -fsS --max-time 5 --write-out '\n' "$BASE_URL/health"
