import asyncio
import uuid
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from redis.asyncio import Redis
from sqlalchemy import String, and_, bindparam, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.exceptions import ConflictError, InventoryError
from app.models.add_on import AddOn
from app.models.add_on_capacity import AddOnCapacity
from app.models.booking import BookingLineItem
from app.models.inventory_buffer import InventoryBuffer
from app.models.inventory_hold import InventoryHold
from app.models.room_type import RoomType


class InventoryService:
    """Core inventory deduction and hold service.

    All write operations (hold, commit, release) run inside a fresh
    database session with ``SERIALIZABLE`` isolation and ``SELECT FOR UPDATE``
    locking.  Deadlocks and serialization failures are retried up to 3
    times with exponential backoff.
    """

    def __init__(self, session: AsyncSession, redis: Redis | None = None):
        self.session = session
        self.redis = redis

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        """Detect PostgreSQL deadlock (40P01) or serialization failure (40001)."""
        if hasattr(exc, "orig") and hasattr(exc.orig, "sqlstate"):
            if exc.orig.sqlstate in ("40P01", "40001"):
                return True
        msg = str(exc).lower()
        return (
            "deadlock detected" in msg
            or "serialization failure" in msg
            or "could not serialize access" in msg
        )

    async def _run_serializable(self, operation):
        """Execute *operation* inside a fresh SERIALIZABLE session.

        *operation* receives the transactional ``AsyncSession``.
        """
        bind = self.session.bind
        if bind is None:
            raise RuntimeError("InventoryService session is not bound to an engine")

        session_maker = async_sessionmaker(
            bind, class_=AsyncSession, expire_on_commit=False
        )
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            async with session_maker() as tx_session:
                try:
                    async with tx_session.begin():
                        await tx_session.execute(
                            text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
                        )
                        result = await operation(tx_session)
                    return result
                except (ConflictError, InventoryError, ValueError):
                    raise
                except Exception as exc:
                    if self._is_retryable(exc) and attempt < max_attempts:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    raise
        raise InventoryError("Operation failed after retries")

    async def check_availability(
        self,
        property_id: uuid.UUID,
        room_type_id: uuid.UUID,
        check_in: date,
        check_out: date,
        exclude_hold_id: uuid.UUID | None = None,
    ) -> int:
        """Return the minimum number of available rooms across all nights
        in *[check_in, check_out)*.

        Parameters
        ----------
        property_id : uuid.UUID
            Property UUID.
        room_type_id : uuid.UUID
            Room type UUID.
        check_in : datetime.date
            Arrival date (inclusive).
        check_out : datetime.date
            Departure date (exclusive).
        exclude_hold_id : uuid.UUID | None
            Optional hold ID to exclude from the count (used during commit).

        Returns
        -------
        int
            Minimum available room count across the requested nights.
        """
        if check_in >= check_out:
            return 0

        stmt = select(RoomType).where(
            RoomType.id == room_type_id,
            RoomType.property_id == property_id,
            RoomType.is_active.is_(True),
            RoomType.is_archived.is_(False),
        )
        result = await self.session.execute(stmt)
        room_type = result.scalar_one_or_none()
        if room_type is None:
            return 0

        total_count = room_type.count

        stmt = select(InventoryHold.dates).where(
            InventoryHold.room_type_id == room_type_id,
            InventoryHold.property_id == property_id,
            or_(
                InventoryHold.status == "committed",
                and_(
                    InventoryHold.status == "active",
                    InventoryHold.expires_at > datetime.now(timezone.utc),
                ),
            ),
        )
        if exclude_hold_id is not None:
            stmt = stmt.where(InventoryHold.id != exclude_hold_id)

        result = await self.session.execute(stmt)
        holds = result.scalars().all()

        hold_counts: Counter = Counter()
        for hold_dates in holds:
            for d in hold_dates:
                if check_in <= d < check_out:
                    hold_counts[d] += 1

        # Query inventory buffers for the date range
        buffer_stmt = select(InventoryBuffer.date, InventoryBuffer.buffer_count).where(
            InventoryBuffer.room_type_id == room_type_id,
            InventoryBuffer.property_id == property_id,
            InventoryBuffer.date >= check_in,
            InventoryBuffer.date < check_out,
        )
        buffer_result = await self.session.execute(buffer_stmt)
        buffer_counts: Counter = Counter()
        for buf_date, buf_count in buffer_result.all():
            buffer_counts[buf_date] += buf_count

        if not hold_counts and not buffer_counts:
            return total_count

        all_dates = set(hold_counts.keys()) | set(buffer_counts.keys())
        max_occupied = max(hold_counts[d] + buffer_counts[d] for d in all_dates)
        available = total_count - max_occupied
        return max(available, 0)

    async def check_addon_availability(
        self,
        add_on_id: uuid.UUID,
        query_date: date,
        slot_time: time | None,
        quantity: int,
    ) -> int:
        """Return available capacity for an add-on on a given date.

        Parameters
        ----------
        add_on_id : uuid.UUID
            Add-on UUID.
        query_date : date
            Date to query.
        slot_time : time | None
            Optional slot time for slot-based add-ons.
        quantity : int
            Requested quantity (must be > 0).

        Returns
        -------
        int
            Available capacity (>= 0).
        """
        if quantity <= 0:
            raise ValueError("quantity must be positive")

        if isinstance(slot_time, str):
            from datetime import datetime as _dt

            slot_time = _dt.strptime(slot_time, "%H:%M:%S").time()

        addon_stmt = select(AddOn).where(AddOn.id == add_on_id)
        addon = (await self.session.execute(addon_stmt)).scalar_one_or_none()
        if addon is None:
            return 0

        if addon.type.value == "package_instance":
            total_capacity = addon.default_capacity if addon.default_capacity > 0 else 9999
        else:
            cap_stmt = select(AddOnCapacity).where(
                AddOnCapacity.add_on_id == add_on_id,
                AddOnCapacity.date == query_date,
            )
            if slot_time is not None:
                cap_stmt = cap_stmt.where(AddOnCapacity.slot_time == slot_time)
            cap_rows = (await self.session.execute(cap_stmt)).scalars().all()
            if not cap_rows:
                return 0
            total_capacity = sum(c.total_capacity for c in cap_rows)

        sql = text(
            """
            WITH booked AS (
                SELECT COALESCE(SUM((elem->>'quantity')::int), 0) AS cnt
                FROM inventory_hold ih
                CROSS JOIN LATERAL jsonb_array_elements(
                    CASE WHEN jsonb_typeof(ih.add_on_holds) = 'array'
                         THEN ih.add_on_holds
                         ELSE '[]'::jsonb
                    END
                ) AS elem
                WHERE ih.status = 'committed'
                  AND elem->>'add_on_id' = :add_on_id
                  AND (elem->>'date')::date = :query_date
                  AND (:slot_time IS NULL OR elem->>'slot_time' = :slot_time)
            ),
            held AS (
                SELECT COALESCE(SUM((elem->>'quantity')::int), 0) AS cnt
                FROM inventory_hold ih
                CROSS JOIN LATERAL jsonb_array_elements(
                    CASE WHEN jsonb_typeof(ih.add_on_holds) = 'array'
                         THEN ih.add_on_holds
                         ELSE '[]'::jsonb
                    END
                ) AS elem
                WHERE ih.status = 'active'
                  AND ih.expires_at > NOW()
                  AND elem->>'add_on_id' = :add_on_id
                  AND (elem->>'date')::date = :query_date
                  AND (:slot_time IS NULL OR elem->>'slot_time' = :slot_time)
            )
            SELECT GREATEST(:total_capacity - b.cnt - h.cnt, 0) AS available
            FROM booked b, held h
            """
        ).bindparams(bindparam("slot_time", type_=String))
        result = await self.session.execute(
            sql,
            {
                "add_on_id": str(add_on_id),
                "query_date": query_date,
                "slot_time": slot_time.isoformat() if slot_time else None,
                "total_capacity": total_capacity,
            },
        )
        row = result.mappings().one_or_none()
        return row.available if row else 0

    async def hold_inventory(
        self,
        booking_id: uuid.UUID,
        property_id: uuid.UUID,
        room_type_id: uuid.UUID,
        dates: list[date],
        add_on_items: list[dict] | None = None,
    ) -> str:
        """Atomically verify availability and create an inventory hold.

        Parameters
        ----------
        booking_id : uuid.UUID
            Placeholder or real booking UUID.
        property_id : uuid.UUID
            Property UUID.
        room_type_id : uuid.UUID
            Room type UUID.
        dates : list[datetime.date]
            Occupied nights.
        add_on_items : list[dict] | None
            Optional add-on holds. Each dict must contain ``add_on_id``,
            ``date``, ``quantity``, and optionally ``slot_time``.

        Returns
        -------
        str
            The generated hold ID (UUID string).

        Raises
        ------
        ValueError
            If *dates* is empty, room type not found, or insufficient
            inventory exists.
        """
        if not dates:
            raise ValueError("dates must not be empty")

        check_in = min(dates)
        check_out = max(dates) + timedelta(days=1)

        # Normalise add-on items so they are JSON-serialisable (strings, not
        # Python date / UUID objects).
        normalised_addons: list[dict] = []
        if add_on_items:
            for item in add_on_items:
                norm = dict(item)
                for key in ("add_on_id", "date", "slot_time"):
                    val = norm.get(key)
                    if isinstance(val, uuid.UUID):
                        norm[key] = str(val)
                    elif isinstance(val, date):
                        norm[key] = val.isoformat()
                    elif isinstance(val, time):
                        norm[key] = val.isoformat()
                normalised_addons.append(norm)

        async def _do_hold(tx_session: AsyncSession) -> str:
            rt_result = await tx_session.execute(
                select(RoomType).where(
                    RoomType.id == room_type_id,
                    RoomType.property_id == property_id,
                    RoomType.is_active.is_(True),
                    RoomType.is_archived.is_(False),
                ).with_for_update()
            )
            room_type = rt_result.scalar_one_or_none()
            if room_type is None:
                raise ValueError("Room type not found")

            svc = InventoryService(tx_session)
            available = await svc.check_availability(
                property_id, room_type_id, check_in, check_out
            )
            if available <= 0:
                raise ValueError("Insufficient inventory")

            if normalised_addons:
                for item in normalised_addons:
                    addon_id = item.get("add_on_id")
                    item_date = item.get("date")
                    slot_time = item.get("slot_time")
                    quantity = item.get("quantity", 1)
                    if not addon_id or not item_date:
                        raise ValueError(
                            "add_on_items must contain add_on_id and date"
                        )
                    if isinstance(addon_id, str):
                        addon_id = uuid.UUID(addon_id)
                    if isinstance(item_date, str):
                        item_date = datetime.strptime(item_date, "%Y-%m-%d").date()
                    addon_avail = await svc.check_addon_availability(
                        addon_id, item_date, slot_time, quantity
                    )
                    if addon_avail < quantity:
                        raise ValueError(
                            f"Insufficient add-on capacity for {addon_id}"
                        )

            hold = InventoryHold(
                org_id=room_type.org_id,
                booking_id=booking_id,
                property_id=property_id,
                room_type_id=room_type_id,
                dates=sorted(set(dates)),
                add_on_holds=normalised_addons or [],
                status="active",
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            )
            tx_session.add(hold)
            await tx_session.flush()
            await tx_session.refresh(hold)
            return str(hold.id)

        hold_id = await self._run_serializable(_do_hold)

        if self.redis:
            await self.redis.setex(
                f"hold:{hold_id}", 600, str(booking_id)
            )

        return hold_id

    async def commit_inventory(self, hold_id: uuid.UUID | str) -> bool:
        """Commit a hold to a confirmed booking.

        Runs inside a ``SERIALIZABLE`` transaction with ``SELECT FOR UPDATE``
        on the relevant inventory rows.

        Parameters
        ----------
        hold_id : uuid.UUID | str
            UUID of the active hold.

        Returns
        -------
        bool
            ``True`` on success, ``False`` if the hold does not exist.

        Raises
        ------
        InventoryError
            If the hold is not active or has expired.
        ConflictError
            If another transaction has taken the inventory.
        """
        if isinstance(hold_id, str):
            hold_id = uuid.UUID(hold_id)

        async def _do_commit(tx_session: AsyncSession) -> bool:
            hold_result = await tx_session.execute(
                select(InventoryHold).where(
                    InventoryHold.id == hold_id
                ).with_for_update()
            )
            hold = hold_result.scalar_one_or_none()
            if hold is None:
                return False
            if hold.status != "active":
                raise InventoryError("Hold is not active")
            if hold.expires_at < datetime.now(timezone.utc):
                raise InventoryError("Hold has expired")

            rt_result = await tx_session.execute(
                select(RoomType).where(
                    RoomType.id == hold.room_type_id,
                    RoomType.property_id == hold.property_id,
                ).with_for_update()
            )
            room_type = rt_result.scalar_one_or_none()
            if room_type is None:
                raise ConflictError("Room type no longer exists")

            svc = InventoryService(tx_session)
            available = await svc.check_availability(
                hold.property_id,
                hold.room_type_id,
                min(hold.dates),
                max(hold.dates) + timedelta(days=1),
                exclude_hold_id=hold.id,
            )
            if available < 1:
                raise ConflictError("Room inventory no longer available")

            tx_session.add(
                BookingLineItem(
                    booking_id=hold.booking_id,
                    item_type="room",
                    item_id=hold.room_type_id,
                    quantity=1,
                    nights=len(hold.dates),
                    unit_price=room_type.default_rate,
                    total_price=room_type.default_rate * len(hold.dates),
                )
            )

            if hold.add_on_holds:
                for ah in hold.add_on_holds:
                    addon_id = ah.get("add_on_id")
                    addon_date = ah.get("date")
                    addon_qty = int(ah.get("quantity", 1))
                    addon_slot = ah.get("slot_time")

                    if isinstance(addon_id, str):
                        addon_id = uuid.UUID(addon_id)
                    if isinstance(addon_date, str):
                        addon_date = datetime.strptime(
                            addon_date, "%Y-%m-%d"
                        ).date()
                    if addon_slot and isinstance(addon_slot, str):
                        addon_slot = datetime.strptime(
                            addon_slot, "%H:%M:%S"
                        ).time()

                    cap_stmt = select(AddOnCapacity).where(
                        AddOnCapacity.add_on_id == addon_id,
                        AddOnCapacity.date == addon_date,
                    )
                    if addon_slot:
                        cap_stmt = cap_stmt.where(
                            AddOnCapacity.slot_time == addon_slot
                        )
                    cap_stmt = cap_stmt.with_for_update()
                    cap_res = await tx_session.execute(cap_stmt)
                    cap = cap_res.scalar_one_or_none()
                    if cap:
                        if cap.available_capacity < addon_qty:
                            raise ConflictError(
                                f"Add-on capacity no longer available for {addon_id}"
                            )
                        cap.available_capacity -= addon_qty
                        cap.updated_at = datetime.now(timezone.utc)

                    addon_stmt = select(AddOn).where(AddOn.id == addon_id)
                    addon = (
                        await tx_session.execute(addon_stmt)
                    ).scalar_one_or_none()
                    unit_price = addon.unit_price if addon else Decimal("0.00")
                    tx_session.add(
                        BookingLineItem(
                            booking_id=hold.booking_id,
                            item_type="add_on",
                            item_id=addon_id,
                            quantity=addon_qty,
                            nights=1,
                            unit_price=unit_price,
                            total_price=unit_price * addon_qty,
                        )
                    )

            hold.status = "committed"
            hold.updated_at = datetime.now(timezone.utc)
            return True

        result = await self._run_serializable(_do_commit)

        if result and self.redis:
            await self.redis.delete(f"hold:{hold_id}")

        return result

    async def release_inventory(self, hold_id: uuid.UUID | str) -> bool:
        """Release a hold and restore availability.

        Runs inside a ``SERIALIZABLE`` transaction with ``SELECT FOR UPDATE``
        on the relevant inventory rows.

        Parameters
        ----------
        hold_id : uuid.UUID | str
            UUID of the hold to release.

        Returns
        -------
        bool
            ``True`` on success.  Idempotent if the hold is already released
            or does not exist.
        """
        if isinstance(hold_id, str):
            hold_id = uuid.UUID(hold_id)

        async def _do_release(tx_session: AsyncSession) -> bool:
            hold_result = await tx_session.execute(
                select(InventoryHold).where(
                    InventoryHold.id == hold_id
                ).with_for_update()
            )
            hold = hold_result.scalar_one_or_none()
            if hold is None:
                return True
            if hold.status == "released":
                return True

            if hold.add_on_holds:
                for ah in hold.add_on_holds:
                    addon_id = ah.get("add_on_id")
                    addon_date = ah.get("date")
                    addon_qty = int(ah.get("quantity", 1))
                    addon_slot = ah.get("slot_time")

                    if isinstance(addon_id, str):
                        addon_id = uuid.UUID(addon_id)
                    if isinstance(addon_date, str):
                        addon_date = datetime.strptime(
                            addon_date, "%Y-%m-%d"
                        ).date()
                    if addon_slot and isinstance(addon_slot, str):
                        addon_slot = datetime.strptime(
                            addon_slot, "%H:%M:%S"
                        ).time()

                    cap_stmt = select(AddOnCapacity).where(
                        AddOnCapacity.add_on_id == addon_id,
                        AddOnCapacity.date == addon_date,
                    )
                    if addon_slot:
                        cap_stmt = cap_stmt.where(
                            AddOnCapacity.slot_time == addon_slot
                        )
                    cap_stmt = cap_stmt.with_for_update()
                    cap_res = await tx_session.execute(cap_stmt)
                    cap = cap_res.scalar_one_or_none()
                    if cap:
                        cap.available_capacity += addon_qty
                        cap.updated_at = datetime.now(timezone.utc)

            hold.status = "released"
            hold.updated_at = datetime.now(timezone.utc)
            return True

        result = await self._run_serializable(_do_release)

        if self.redis:
            await self.redis.delete(f"hold:{hold_id}")

        return result
