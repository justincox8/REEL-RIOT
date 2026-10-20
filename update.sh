#!/bin/bash
set -euo pipefail

cd /home/justin/mediarecs

echo "===== Weekly catalog update started: $(date) ====="

echo "Step 1: Updating books..."
uv run python populate_books.py

echo "Step 2: Updating movies..."
uv run python populate_movies.py

echo "Step 3: Recalculating embeddings..."
uv run python recalc.py

echo "===== Weekly catalog update completed: $(date) ====="
