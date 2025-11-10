#!/bin/bash

# Generate Alembic migration with autogenerate support
# Usage: ./scripts/generate_migration.sh "migration message"

if [ -z "$1" ]; then
    echo "Error: Migration message required"
    echo 'Usage: ./scripts/generate_migration.sh "migration message"'
    exit 1
fi

MESSAGE="$1"

echo "Generating migration: $MESSAGE"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.." || exit 1

if [ -d "venv" ]; then
    # shellcheck disable=SC1091
    source venv/bin/activate
fi

alembic revision --autogenerate -m "$MESSAGE"

echo "[OK] Migration generated"
echo "Review the migration file in migrations/versions/"
echo "Apply with: alembic upgrade head"

