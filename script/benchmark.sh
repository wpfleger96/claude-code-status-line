#!/usr/bin/env bash

set -euo pipefail

PYTEST_CMD="uv run pytest -m performance"

case "${1:-help}" in
    compare)
        # Compare against last saved run (don't save current)
        echo "Comparing against last benchmark..."
        $PYTEST_CMD --benchmark-compare
        ;;

    save)
        # Save current run as new baseline
        echo "Running and saving benchmark..."
        $PYTEST_CMD --benchmark-autosave
        ;;

    record)
        # Compare AND save (for "official" runs)
        echo "Running, comparing, and saving benchmark..."
        $PYTEST_CMD --benchmark-compare --benchmark-autosave
        ;;

    list)
        # List saved benchmarks
        if [ -d .benchmarks ]; then
            echo "Saved benchmarks:"
            ls -lh .benchmarks/*/
        else
            echo "No saved benchmarks found"
        fi
        ;;

    clean)
        # Clean all saved benchmarks
        if [ -d .benchmarks ]; then
            echo "Removing all saved benchmarks..."
            rm -rf .benchmarks/
        else
            echo "No saved benchmarks found"
        fi
        ;;

    help|*)
        cat <<EOF
Usage: $0 <command>

Commands:
  compare  - Compare current code against last saved benchmark (default workflow)
  save     - Run and save benchmark as new baseline (first run)
  record   - Compare AND save (use after confirming improvements)
  list     - List all saved benchmark files
  clean    - Remove all saved benchmarks
  help     - Show this help message

Typical workflow:
  1. ./script/benchmark.sh save          # Initial baseline
  2. [make changes]
  3. ./script/benchmark.sh compare       # See if faster (iterate)
  4. ./script/benchmark.sh record        # Save the good result
EOF
        ;;
esac
