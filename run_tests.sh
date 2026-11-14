#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "=== Backend tests ==="
cd backend
python3 -m pytest tests/ -v "$@"

echo ""
echo "=== Frontend tests ==="
cd ../frontend
npx vitest run
