#!/bin/bash
set -e

echo "[entrypoint] Validating environment variables..."
python scripts/validate_env.py

echo "[entrypoint] Starting $@"
exec "$@"
