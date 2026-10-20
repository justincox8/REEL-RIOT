#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

echo "===== Catalog update started: $(date) ====="

uv run python populate_books.py
uv run python populate_movies.py
uv run python recalc.py

echo "===== Catalog update completed: $(date) ====="
