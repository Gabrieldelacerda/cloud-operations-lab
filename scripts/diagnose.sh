#!/usr/bin/env bash
set -uo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$PROJECT_DIR" || exit 1

result=0

printf '\nCompose configuration\n'
docker compose config --quiet || result=1

printf '\nContainer status\n'
docker compose ps -a || result=1

printf '\nRecent logs\n'
docker compose logs --no-color --tail 50 || result=1

printf '\nHTTP health response\n'
curl --fail --silent --show-error --include \
  --max-time 5 http://127.0.0.1:8088/health || result=1

printf '\n'
exit "$result"
