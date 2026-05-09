import asyncio
import os
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.security import get_password_hash
from app.db.base import Base
from app.models.organization import Organization
from app.models.role import Role
from app.models.user import User
from app.models.property import Property
from app.models.room_type import RoomType
from app.models.ota_mapping import OTAMapping
from app.models.raw_email import RawEmail
from app.models.parsed_booking import ParsedBookingQueue
from app.models.user_property import UserProperty

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
MANAGER_EMAIL = "e2e-manager@brekora.test"
MANAGER_PASSWORD = "E2EManager123!"


async def seed():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not set")

    async_url = database_url.replace("postgresql+psycopg://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        org = await session.get(Organization, DEFAULT_ORG_ID)
        if not org:
            print("Default org not found, skipping seed.")
            return

        result = await session.execute(
            select(Role).where(Role.name == "Manager", Role.org_id == DEFAULT_ORG_ID)
        )
        manager_role = result.scalar_one_or_none()
        if not manager_role:
            print("Manager role not found, skipping seed.")
            return

        result = await session.execute(
            select(User).where(User.email == MANAGER_EMAIL, User.org_id == DEFAULT_ORG_ID)
        )
        if result.scalar_one_or_none():
            print("E2E data already seeded.")
            return

        user = User(
            org_id=DEFAULT_ORG_ID,
            email=MANAGER_EMAIL,
            password_hash=get_password_hash(MANAGER_PASSWORD),
            first_name="E2E",
            last_name="Manager",
            role_id=manager_role.id,
            is_active=True,
        )
        session.add(user)

        prop = Property(
            org_id=DEFAULT_ORG_ID,
            name="E2E Test Property",
            address="123 Test Lane, Test City",
            is_active=True,
        )
        session.add(prop)
        await session.flush()

        user_property = UserProperty(
            user_id=user.id,
            property_id=prop.id,
            role_at_property="manager",
            is_active=True,
        )
        session.add(user_property)

        room = RoomType (
            org_id=DEFAULT_ORG_ID,
            property_id=prop.id,
            name="Standard Room",
            description="A comfy standard room for E2E tests",
            count=5,
            base_capacity=2,
            max_capacity=3,
            default_rate=1500.00,
            is_active=True,
        )
        session.add(room)
        await session.flush()

        mapping = OTAMapping(
            org_id=DEFAULT_ORG_ID,
            ota_source="airbnb",
            listing_id="e2e-airbnb-001",
            property_id=prop.id,
            room_type_id=room.id,
            is_active=True,
        )
        session.add(mapping)

        raw_email = RawEmail(
            org_id=DEFAULT_ORG_ID,
            gmail_message_id="e2e-msg-001",
            ota_source="airbnb",
            sender="airbnb@airbnb.com",
            subject="Reservation confirmed",
            body_text="Test booking body",
            received_at="2026-05-01T10:00:00",
            status="pending",
        )
        session.add(raw_email)
        await session.flush()

        queue_item = ParsedBookingQueue(
            org_id=DEFAULT_ORG_ID,
            source_type="airbnb",
            raw_email_id=raw_email.id,
            ota_reference_id="AIR-E2E-001",
            parsed_data={
                "guest_name": "Alice E2E",
                "guest_email": "alice@example.com",
                "check_in": "2026-06-01",
                "check_out": "2026-06-03",
                "number_of_guests": 2,
                "gross_amount": "3000.00",
                "property_name": "E2E Test Property",
                "listing_id": "e2e-airbnb-001",
                "room_type": "Standard Room",
            },
            confidence_score=0.95,
            status="pending",
        )
        session.add(queue_item)

        await session.commit()
        print(
            f"Seeded E2E data: property={prop.id}, room={room.id}, user={user.id}, queue={queue_item.id}"
        )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
