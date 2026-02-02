#!/usr/bin/env bash
#
# Run all Python tests for the api-ai-agent project.
#
# Usage:
#   ./scripts/run_tests.sh           # Run unit tests (excludes integration tests that need API/DB)
#   ./scripts/run_tests.sh --all     # Run all tests including integration (requires API running for test_internal_api)
#

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"
export TZ=UTC

RUN_ALL=false
EXTRA_ARGS=()
for arg in "$@"; do
  case $arg in
    --all)
      RUN_ALL=true
      ;;
    *)
      EXTRA_ARGS+=("$arg")
      ;;
  esac
done

# Use uv if available, otherwise python -m
if command -v uv &> /dev/null; then
  RUNNER="uv run"
else
  RUNNER="python -m"
fi

# Ensure pytest can import src (project root in path)
export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"

# Exclude test_internal_api by default (requires running API server at localhost:8000)
# Use --all to include it (API must be running)
if [ "$RUN_ALL" = true ]; then
  echo "Running all tests (including integration tests)..."
  $RUNNER pytest tests/ -v "${EXTRA_ARGS[@]}"
else
  echo "Running unit tests (excluding test_internal_api which requires API server)..."
  $RUNNER pytest tests/ -v --ignore=tests/test_internal_api.py "${EXTRA_ARGS[@]}"
fi
