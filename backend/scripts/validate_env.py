"""Validate required environment variables at container startup."""
import os
import sys


REQUIRED_VARS = [
    "DATABASE_URL",
    "SECRET_KEY",
    "REDIS_URL",
]


def main():
    missing = [var for var in REQUIRED_VARS if not os.getenv(var)]
    if missing:
        print(
            f"[validate_env] Missing required environment variables: {', '.join(missing)}",
            file=sys.stderr,
        )
        sys.exit(1)
    print("[validate_env] Environment variables validated successfully")


if __name__ == "__main__":
    main()
