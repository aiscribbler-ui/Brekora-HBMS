import asyncio
import os
import subprocess
import sys

# Ensure the backend app is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import get_settings


async def reset_database():
    settings = get_settings()
    sync_url = settings.sync_database_url

    from sqlalchemy import create_engine, text

    print("Connecting to database...")
    engine = create_engine(sync_url, isolation_level="AUTOCOMMIT")

    with engine.connect() as conn:
        print("Dropping public schema...")
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        print("Recreating public schema...")
        conn.execute(text("CREATE SCHEMA public"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO CURRENT_USER"))

    engine.dispose()
    print("Database schema reset.")

    print("Running Alembic migrations...")
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "heads"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("Alembic failed:")
        print(result.stdout)
        print(result.stderr)
        sys.exit(1)
    print("Migrations applied successfully.")


async def clear_redis():
    settings = get_settings()
    redis_url = settings.REDIS_URL

    if not redis_url:
        print("WARNING: REDIS_URL not set, skipping Redis cleanup.")
        return

    try:
        import redis.asyncio as redis
    except ImportError:
        print("WARNING: redis package not installed, skipping Redis cleanup.")
        return

    print("Clearing Redis...")
    client = redis.from_url(redis_url)
    await client.flushdb()
    await client.close()
    print("Redis flushed.")


async def main():
    force = "--yes" in sys.argv or "-y" in sys.argv

    print("=== Brekora Setup Reset ===")
    print()
    print("This will WIPE the entire database and all Redis sessions.")
    print("You will need to run the admin setup again from the frontend.")
    print()

    if not force:
        confirm = input("Type 'reset' to confirm: ")
        if confirm.strip().lower() != "reset":
            print("Aborted.")
            return

    await reset_database()
    await clear_redis()

    print()
    print("=== Done ===")
    print("Database is clean. Start the backend and visit the frontend to run setup.")


if __name__ == "__main__":
    asyncio.run(main())
