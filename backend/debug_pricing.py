import asyncio
import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine
from app.models import Base
from testcontainers.postgres import PostgresContainer
from app.repositories.pricing import RatePlanRepository


async def main():
    with PostgresContainer('postgres:15-alpine', driver='psycopg') as pg:
        url = pg.get_connection_url().replace('postgresql+psycopg2://', 'postgresql+psycopg://')
        sync_url = url
        alembic_cfg = Config('alembic.ini')
        alembic_cfg.set_main_option('sqlalchemy.url', sync_url)
        command.upgrade(alembic_cfg, 'heads')

        async_url = url.replace('postgresql+psycopg://', 'postgresql+asyncpg://')
        engine = create_async_engine(async_url, poolclass=NullPool, future=True)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        session = async_session()
        try:
            org_id = uuid.UUID('00000000-0000-0000-0000-000000000001')
            repo = RatePlanRepository(session, org_id)
            rp = await repo.create({'name': 'Test', 'code': 'TEST1', 'discount_type': 'percentage', 'discount_value': Decimal('0.00')})
            print(f'Created: {rp.id}, is_active={rp.is_active}')

            found = await repo.get(rp.id)
            print(f'Found before update: {found is not None}, is_active={found.is_active if found else None}')

            updated = await repo.update(found, {'is_active': False})
            print(f'Updated: is_active={updated.is_active}')

            found2 = await repo.get(rp.id)
            print(f'Found after update: {found2 is not None}, is_active={found2.is_active if found2 else None}')
        finally:
            await session.rollback()
            await session.close()
            await engine.dispose()

            engine_sync = create_engine(sync_url)
            Base.metadata.drop_all(engine_sync)
            engine_sync.dispose()


if __name__ == "__main__":
    asyncio.run(main())
