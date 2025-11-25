#!/usr/bin/env bash

set -euo pipefail

STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACMR 2>/dev/null || true)

echo "Syncing dependencies"
uv sync

echo "Running linter"
uvx ruff check . --fix

echo "Running formatting"
uvx ruff format .

if [ -n "$STAGED_FILES" ]; then
    for file in $STAGED_FILES; do
        if [ -f "$file" ] && ! git diff --quiet -- "$file" 2>/dev/null; then
            echo "Re-staging formatted/linted file: $file"
            git add "$file"
        fi
    done
fi

if [ -n "${RUN_TESTS:-}" ]; then
    echo "Running tests"
    uv run pytest
fi
