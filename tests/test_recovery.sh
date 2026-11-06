#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$PROJECT_DIR"

APP_ID=""
RESTORE_NEEDED=0
HEALTH_URL="http://127.0.0.1:8088/health"

fail() {
  echo "[FAIL] $*" >&2
  exit 1
}

cleanup() {
  local status=$?
  trap - EXIT
  if [[ "$RESTORE_NEEDED" == 1 ]]; then
    echo "Restoring the application after an incomplete test..." >&2
    if ! docker start "$APP_ID" >/dev/null; then
      echo "[FAIL] Restore manually: docker compose up -d --wait app" >&2
      status=1
    fi
  fi
  exit "$status"
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

APP_ID=$(docker compose ps -q app)
NGINX_ID=$(docker compose ps -q nginx)
[[ -n "$APP_ID" && -n "$NGINX_ID" ]] ||
  fail "Start the lab first: docker compose up -d --build --wait"

[[ "$(docker inspect --format '{{.State.Running}}' "$APP_ID")" == true ]] ||
  fail "The application must be running before this test"
[[ "$(docker inspect --format '{{.State.Running}}' "$NGINX_ID")" == true ]] ||
  fail "Nginx must be running before this test"
NGINX_STARTED=$(docker inspect --format '{{.State.StartedAt}}' "$NGINX_ID")

python3 tests/http_smoke.py

echo "Stopping the backend for a controlled outage..."
RESTORE_NEEDED=1
docker compose stop app

HTTP_CODE=$(curl --silent --show-error --output /dev/null \
  --write-out '%{http_code}' --max-time 8 "$HEALTH_URL")
[[ "$HTTP_CODE" == 502 || "$HTTP_CODE" == 504 ]] ||
  fail "Expected HTTP 502 or 504 during the outage; received $HTTP_CODE"
echo "[ OK ] Backend outage returned HTTP $HTTP_CODE"

docker start "$APP_ID" >/dev/null
READY=0
DEADLINE=$((SECONDS + 45))
while (( SECONDS < DEADLINE )); do
  if HTTP_CODE=$(curl --silent --output /dev/null \
    --write-out '%{http_code}' --max-time 5 "$HEALTH_URL") &&
    [[ "$HTTP_CODE" == 200 ]]; then
    READY=1
    break
  fi
  sleep 1
done
[[ "$READY" == 1 ]] || fail "HTTP 200 did not return after restoring the backend"

python3 tests/http_smoke.py

echo "Waiting for application and proxy healthchecks..."
HEALTHY=0
DEADLINE=$((SECONDS + 45))
while (( SECONDS < DEADLINE )); do
  APP_HEALTH=$(docker inspect --format '{{.State.Health.Status}}' "$APP_ID")
  NGINX_HEALTH=$(docker inspect --format '{{.State.Health.Status}}' "$NGINX_ID")

  if [[ "$APP_HEALTH" == healthy && "$NGINX_HEALTH" == healthy ]]; then
    HEALTHY=1
    break
  fi
  sleep 1
done
[[ "$HEALTHY" == 1 ]] ||
  fail "Healthchecks did not recover: app=$APP_HEALTH nginx=$NGINX_HEALTH"

[[ "$(docker compose ps -q nginx)" == "$NGINX_ID" ]] ||
  fail "The Nginx container was replaced during recovery"
[[ "$(docker inspect --format '{{.State.Running}}' "$NGINX_ID")" == true ]] ||
  fail "Nginx is no longer running"
[[ "$(docker inspect --format '{{.State.StartedAt}}' "$NGINX_ID")" == "$NGINX_STARTED" ]] ||
  fail "Nginx restarted during recovery"

RESTORE_NEEDED=0
echo "[ OK ] Both container healthchecks recovered"
echo "[ OK ] HTTP 200 restored without restarting Nginx"
