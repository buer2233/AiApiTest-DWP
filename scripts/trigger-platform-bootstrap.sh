#!/usr/bin/env bash
set -euo pipefail

BUILD_ALL=true
RUN_FULL_TESTS=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --build-all)
      [[ $# -ge 2 ]] || { echo "--build-all requires true or false" >&2; exit 2; }
      BUILD_ALL="$2"
      shift 2
      ;;
    --run-full-tests)
      [[ $# -ge 2 ]] || { echo "--run-full-tests requires true or false" >&2; exit 2; }
      RUN_FULL_TESTS="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

for value in "$BUILD_ALL" "$RUN_FULL_TESTS"; do
  [[ "$value" == "true" || "$value" == "false" ]] || {
    echo "Boolean arguments must be true or false" >&2
    exit 2
  }
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CORE_SCRIPT="$REPO_ROOT/jenkins/scripts/platform_bootstrap_cli.py"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python)"
else
  echo "Python was not found on PATH. Install Python, then rerun this trigger command." >&2
  exit 1
fi

cd "$REPO_ROOT"
exec "$PYTHON_BIN" "$CORE_SCRIPT" trigger \
  --build-all "$BUILD_ALL" \
  --run-full-tests "$RUN_FULL_TESTS"
