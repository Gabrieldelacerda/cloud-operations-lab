#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$PROJECT_DIR"

RESTORE_NEEDED=0
OUTPUT=$(mktemp)

fail() {
  echo "[FAIL] $*" >&2
  cat "$OUTPUT" >&2
  exit 1
}

restore_app() {
  docker compose up -d --wait --wait-timeout 60 app
}

cleanup() {
  local status=$?
  trap - EXIT

  if [[ "$RESTORE_NEEDED" == 1 ]]; then
    echo "Attempting backend recovery after an incomplete test..." >&2
    if ! restore_app; then
      echo "[FAIL] Restore manually: docker compose up -d --wait app" >&2
      status=1
    fi
  fi

  rm -f -- "$OUTPUT"
  exit "$status"
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if bash scripts/diagnose.sh >"$OUTPUT" 2>&1; then
  echo "[ OK ] Diagnostics passed with healthy services"
else
  fail "Diagnostics failed before the outage"
fi

RESTORE_NEEDED=1
docker compose stop app

if bash scripts/diagnose.sh >"$OUTPUT" 2>&1; then
  fail "Diagnostics incorrectly passed with the backend stopped"
else
  status=$?
  [[ "$status" == 1 ]] ||
    fail "Expected diagnostic exit code 1; received $status"
fi

grep -Fq '[FAIL] app: expected running healthy' "$OUTPUT" ||
  fail "Diagnostics did not identify the stopped application"

echo "[ OK ] Diagnostics identified the stopped backend and exited with code 1"

restore_app
RESTORE_NEEDED=0

if bash scripts/diagnose.sh >"$OUTPUT" 2>&1; then
  echo "[ OK ] Diagnostics passed after backend recovery"
else
  fail "Diagnostics failed after recovery"
fi

echo "[ OK ] All diagnostic tests passed"
