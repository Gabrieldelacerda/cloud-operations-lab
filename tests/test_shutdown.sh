#!/usr/bin/env bash
set -euo pipefail

IMAGE=${IMAGE:-cloud-operations-lab:local}
CONTAINER_ID=""

fail() {
  echo "[FAIL] $*" >&2
  exit 1
}

cleanup() {
  if [[ -n "$CONTAINER_ID" ]]; then
    docker rm -f "$CONTAINER_ID" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

command -v docker >/dev/null 2>&1 || fail "Docker is required"
docker info >/dev/null 2>&1 || fail "Cannot access Docker Engine"
docker image inspect "$IMAGE" >/dev/null 2>&1 ||
  fail "Image not found: $IMAGE. Run: docker compose build app"

for SIGNAL in SIGTERM SIGINT; do
  echo "Testing $SIGNAL with image $IMAGE..."

  CONTAINER_ID=$(docker run -d --pull never --network none "$IMAGE")
  READY=0

  for ((ATTEMPT = 1; ATTEMPT <= 20; ATTEMPT++)); do
    if docker exec "$CONTAINER_ID" python -c \
      "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=1).close()" \
      >/dev/null 2>&1; then
      READY=1
      break
    fi
    sleep 0.2
  done

  if [[ "$READY" != 1 ]]; then
    docker logs "$CONTAINER_ID" >&2 || true
    fail "Application did not become ready before testing $SIGNAL"
  fi

  docker stop --signal "$SIGNAL" --timeout 3 "$CONTAINER_ID" >/dev/null

  STATE=$(docker inspect --format \
    '{{.State.ExitCode}} {{.State.OOMKilled}}' "$CONTAINER_ID")

  [[ "$STATE" == "0 false" ]] ||
    fail "$SIGNAL: expected exit=0 and OOMKilled=false; received $STATE"

  LOGS=$(docker logs "$CONTAINER_ID" 2>&1)
  [[ "$LOGS" == *"Application stopped cleanly"* ]] ||
    fail "$SIGNAL: clean shutdown message was not found"

  docker rm "$CONTAINER_ID" >/dev/null
  CONTAINER_ID=""

  echo "[ OK ] $SIGNAL: exit=0, OOMKilled=false, clean shutdown logged"
done

echo "[ OK ] All shutdown tests passed"
