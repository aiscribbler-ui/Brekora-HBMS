#!/bin/bash
set -e

echo "[entrypoint] Validating environment variables..."
python scripts/validate_env.py

echo "[entrypoint] Running database migrations..."
alembic upgrade heads || true

echo "[entrypoint] Starting $@"
exec "$@"
