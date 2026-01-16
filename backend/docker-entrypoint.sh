#!/bin/bash
set -e

echo "Running database migrations..."
PYTHONPATH=/app uv run alembic upgrade head

echo "Migrations completed, starting backend..."
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
