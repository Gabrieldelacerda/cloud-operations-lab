#!/usr/bin/env bash
set -uo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$PROJECT_DIR" || exit 1

result=0

printf '\nCompose configuration\n'
docker compose config --quiet || result=1

printf '\nContainer status\n'
docker compose ps -a || result=1

printf '\nService health\n'
for service in app nginx; do
  if ! container_id=$(docker compose ps -aq "$service"); then
    result=1
    continue
  fi

  if [[ -z "$container_id" ]]; then
    printf '[FAIL] %s: container missing\n' "$service"
    result=1
    continue
  fi

  if ! state=$(docker inspect --format \
    '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}' \
    "$container_id"); then
    result=1
    continue
  fi

  printf '%s: %s\n' "$service" "$state"
  if [[ "$state" != "running healthy" ]]; then
    printf '[FAIL] %s: expected running healthy\n' "$service"
    result=1
  fi
done

printf '\nRecent logs\n'
docker compose logs --no-color --tail 50 || result=1

printf '\nHTTP health response\n'
curl --fail --silent --show-error --include \
  --write-out '\n' --max-time 5 \
  http://127.0.0.1:8088/health || result=1

exit "$result"
