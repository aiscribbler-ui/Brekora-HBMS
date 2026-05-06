"""Health check script for the worker service."""
import os
import sys
import time

import redis


def main() -> None:
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    health_key = os.getenv("ARQ_HEALTH_KEY", "arq:health")
    stale_threshold_seconds = 60

    try:
        client = redis.Redis.from_url(
            redis_url,
            socket_connect_timeout=5,
            socket_timeout=5,
            decode_responses=True,
        )

        if not client.ping():
            print("Redis ping failed")
            sys.exit(1)

        timestamp = client.get(health_key)
        if timestamp is None:
            print("Worker health key not found")
            sys.exit(1)

        # ARQ health key contains a human-readable string like:
        # "May-04 03:37:50 j_complete=7 j_failed=0 ..."
        # We just verify it exists and contains expected fields.
        if "j_complete=" not in timestamp:
            print(f"Worker health key has unexpected format: {timestamp}")
            sys.exit(1)

        print("Worker healthy")
        sys.exit(0)
    except Exception as exc:
        print(f"Health check error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
