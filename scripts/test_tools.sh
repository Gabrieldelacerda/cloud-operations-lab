#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$PROJECT_DIR"

tests=(
  tests/test_log_records.py
  tests/test_find_request.py
  tests/test_summarize_proxy_logs.py
  tests/test_render_proxy_summary.py
  tests/test_render_slow_backend_summary.py
)

for test_file in "${tests[@]}"; do
  printf '\nRunning %s\n' "$test_file"
  python3 -B "$test_file"
done

printf '\n[ OK ] All offline tool tests passed\n'
