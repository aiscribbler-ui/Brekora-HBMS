import json
import uuid
from datetime import date, time

from redis.asyncio import Redis
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.add_on import AddOn
from app.models.room_type import RoomType


class AvailabilityService:
    """Query engine for room and add-on availability."""

    def __init__(self, session: AsyncSession, redis: Redis | None = None):
        self.session = session
        self.redis = redis

    @staticmethod
    def _cache_key(
        property_id: uuid.UUID,
        room_type_id: uuid.UUID,
        check_in: date,
        check_out: date,
    ) -> str:
        return (
            f"avail:rooms:{property_id}:{room_type_id}"
            f":{check_in.isoformat()}:{check_out.isoformat()}"
        )

    @staticmethod
    def _addon_cache_key(
        add_on_id: uuid.UUID,
        query_date: date,
        slot_time: time | None = None,
    ) -> str:
        slot = slot_time.isoformat() if slot_time else "all"
        return f"avail:addon:{add_on_id}:{query_date.isoformat()}:{slot}"

    @staticmethod
    def _addon_range_cache_key(
        add_on_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> str:
        return (
            f"avail:addon:range:{add_on_id}"
            f":{start_date.isoformat()}:{end_date.isoformat()}"
        )

    async def get_room_availability(
        self,
        property_id: uuid.UUID,
        room_type_id: uuid.UUID,
        check_in: date,
        check_out: date,
        org_id: uuid.UUID | None = None,
    ) -> list[dict]:
        """Return availability per night for the requested date range.

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
        org_id : uuid.UUID | None
            Optional organization UUID for scoping.

        Returns
        -------
        list[dict]
            One dict per night with keys: date, available_count, total_count,
            booked_count, held_count.
        """
        if check_in >= check_out:
            return []

        cache_key = self._cache_key(property_id, room_type_id, check_in, check_out)

        if self.redis is not None:
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)

        # Verify room type exists and is active.
        rt_stmt = select(RoomType).where(
            RoomType.id == room_type_id,
            RoomType.property_id == property_id,
            RoomType.is_active.is_(True),
            RoomType.is_archived.is_(False),
        )
        if org_id is not None:
            rt_stmt = rt_stmt.where(RoomType.org_id == org_id)

        result = await self.session.execute(rt_stmt)
        room_type = result.scalar_one_or_none()
        if room_type is None:
            return []

        total_count = room_type.count

        # Single efficient CTE query for per-night availability.
        sql = text(
            """
            WITH date_series AS (
                SELECT generate_series(CAST(:check_in AS date), CAST(:check_out AS date) - interval '1 day', interval '1 day')::date AS night
            ),
            booked AS (
                SELECT d.night, COUNT(*) AS cnt
                FROM inventory_hold ih
                CROSS JOIN LATERAL unnest(ih.dates) AS d(night)
                WHERE ih.property_id = CAST(:property_id AS uuid)
                  AND ih.room_type_id = CAST(:room_type_id AS uuid)
                  AND ih.status = 'committed'
                  AND d.night BETWEEN CAST(:check_in AS date) AND CAST(:check_out AS date) - interval '1 day'
                GROUP BY d.night
            ),
            held AS (
                SELECT d.night, COUNT(*) AS cnt
                FROM inventory_hold ih
                CROSS JOIN LATERAL unnest(ih.dates) AS d(night)
                WHERE ih.property_id = CAST(:property_id AS uuid)
                  AND ih.room_type_id = CAST(:room_type_id AS uuid)
                  AND ih.status = 'active'
                  AND ih.expires_at > NOW()
                  AND d.night BETWEEN CAST(:check_in AS date) AND CAST(:check_out AS date) - interval '1 day'
                GROUP BY d.night
            ),
            buffered AS (
                SELECT ib.date AS night, COALESCE(SUM(ib.buffer_count), 0) AS cnt
                FROM inventory_buffer ib
                WHERE ib.property_id = CAST(:property_id AS uuid)
                  AND ib.room_type_id = CAST(:room_type_id AS uuid)
                  AND ib.date BETWEEN CAST(:check_in AS date) AND CAST(:check_out AS date) - interval '1 day'
                GROUP BY ib.date
            )
            SELECT
                ds.night AS date,
                CAST(:total_count AS int) AS total_count,
                COALESCE(b.cnt, 0) AS booked_count,
                COALESCE(h.cnt, 0) AS held_count,
                COALESCE(buf.cnt, 0) AS buffer_count,
                GREATEST(CAST(:total_count AS int) - COALESCE(b.cnt, 0) - COALESCE(h.cnt, 0) - COALESCE(buf.cnt, 0), 0) AS available_count
            FROM date_series ds
            LEFT JOIN booked b ON b.night = ds.night
            LEFT JOIN held h ON h.night = ds.night
            LEFT JOIN buffered buf ON buf.night = ds.night
            ORDER BY ds.night;
            """
        )

        result = await self.session.execute(
            sql,
            {
                "check_in": check_in,
                "check_out": check_out,
                "property_id": str(property_id),
                "room_type_id": str(room_type_id),
                "total_count": total_count,
            },
        )

        rows = [
            {
                "date": row.date,
                "total_count": row.total_count,
                "booked_count": row.booked_count,
                "held_count": row.held_count,
                "buffer_count": row.buffer_count,
                "available_count": row.available_count,
            }
            for row in result.mappings().all()
        ]

        if self.redis is not None:
            await self.redis.setex(cache_key, 30, json.dumps(rows, default=str))

        return rows

    async def get_addon_availability(
        self,
        add_on_id: uuid.UUID,
        query_date: date,
        slot_time: time | None = None,
    ) -> list[dict]:
        """Return availability for an add-on on a specific date.

        Parameters
        ----------
        add_on_id : uuid.UUID
            Add-on UUID.
        query_date : date
            Date to query.
        slot_time : time | None
            Optional slot time for slot-based add-ons.

        Returns
        -------
        list[dict]
            One dict per slot/day with keys: date, slot_time (optional),
            available_capacity, total_capacity, booked_count, held_count.
        """
        cache_key = self._addon_cache_key(add_on_id, query_date, slot_time)

        if self.redis is not None:
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)

        # Verify add-on exists.
        addon_stmt = select(AddOn).where(AddOn.id == add_on_id)
        result = await self.session.execute(addon_stmt)
        add_on = result.scalar_one_or_none()
        if add_on is None:
            return []

        addon_type = add_on.type
        rows: list[dict] = []

        if addon_type == "package_instance":
            total_capacity = add_on.default_capacity if add_on.default_capacity > 0 else 9999

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
                      AND (elem->>'add_on_id')::uuid = CAST(:add_on_id AS uuid)
                      AND (elem->>'date')::date = CAST(:query_date AS date)
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
                      AND (elem->>'add_on_id')::uuid = CAST(:add_on_id AS uuid)
                      AND (elem->>'date')::date = CAST(:query_date AS date)
                )
                SELECT CAST(:query_date AS date) AS date,
                       CAST(:total_capacity AS int) AS total_capacity,
                       b.cnt AS booked_count,
                       h.cnt AS held_count,
                       GREATEST(CAST(:total_capacity AS int) - b.cnt - h.cnt, 0) AS available_capacity
                FROM booked b, held h
                """
            )
            result = await self.session.execute(
                sql,
                {
                    "add_on_id": str(add_on_id),
                    "query_date": query_date,
                    "total_capacity": total_capacity,
                },
            )
            row = result.mappings().one_or_none()
            if row:
                rows.append(
                    {
                        "date": row.date,
                        "slot_time": None,
                        "total_capacity": row.total_capacity,
                        "booked_count": row.booked_count,
                        "held_count": row.held_count,
                        "available_capacity": row.available_capacity,
                    }
                )

        elif addon_type == "slot":
            capacity_sql = text(
                """
                SELECT date, slot_time, total_capacity
                FROM add_on_capacity
                WHERE add_on_id = CAST(:add_on_id AS uuid)
                  AND date = CAST(:query_date AS date)
                """
                + (" AND slot_time = CAST(:slot_time AS time)" if slot_time is not None else "")
                + " ORDER BY slot_time"
            )
            params: dict = {
                "add_on_id": str(add_on_id),
                "query_date": query_date,
            }
            if slot_time is not None:
                params["slot_time"] = slot_time

            cap_result = await self.session.execute(capacity_sql, params)
            capacities = cap_result.mappings().all()
            if not capacities:
                return []

            for cap in capacities:
                cap_slot_time = cap.slot_time
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
                          AND (elem->>'add_on_id')::uuid = CAST(:add_on_id AS uuid)
                          AND (elem->>'date')::date = CAST(:query_date AS date)
                          AND (elem->>'slot_time')::time = CAST(:slot_time AS time)
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
                          AND (elem->>'add_on_id')::uuid = CAST(:add_on_id AS uuid)
                          AND (elem->>'date')::date = CAST(:query_date AS date)
                          AND (elem->>'slot_time')::time = CAST(:slot_time AS time)
                    )
                    SELECT CAST(:query_date AS date) AS date,
                           CAST(:slot_time AS time) AS slot_time,
                           CAST(:total_capacity AS int) AS total_capacity,
                           b.cnt AS booked_count,
                           h.cnt AS held_count,
                           GREATEST(CAST(:total_capacity AS int) - b.cnt - h.cnt, 0) AS available_capacity
                    FROM booked b, held h
                    """
                )
                result = await self.session.execute(
                    sql,
                    {
                        "add_on_id": str(add_on_id),
                        "query_date": query_date,
                        "slot_time": cap_slot_time,
                        "total_capacity": cap.total_capacity,
                    },
                )
                row = result.mappings().one_or_none()
                if row:
                    rows.append(
                        {
                            "date": row.date,
                            "slot_time": row.slot_time,
                            "total_capacity": row.total_capacity,
                            "booked_count": row.booked_count,
                            "held_count": row.held_count,
                            "available_capacity": row.available_capacity,
                        }
                    )

        elif addon_type == "day":
            sql = text(
                """
                WITH capacities AS (
                    SELECT COALESCE(SUM(total_capacity), 0) AS total_capacity
                    FROM add_on_capacity
                    WHERE add_on_id = CAST(:add_on_id AS uuid)
                      AND date = CAST(:query_date AS date)
                ),
                booked AS (
                    SELECT COALESCE(SUM((elem->>'quantity')::int), 0) AS cnt
                    FROM inventory_hold ih
                    CROSS JOIN LATERAL jsonb_array_elements(
                        CASE WHEN jsonb_typeof(ih.add_on_holds) = 'array'
                             THEN ih.add_on_holds
                             ELSE '[]'::jsonb
                        END
                    ) AS elem
                    WHERE ih.status = 'committed'
                      AND (elem->>'add_on_id')::uuid = CAST(:add_on_id AS uuid)
                      AND (elem->>'date')::date = CAST(:query_date AS date)
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
                      AND (elem->>'add_on_id')::uuid = CAST(:add_on_id AS uuid)
                      AND (elem->>'date')::date = CAST(:query_date AS date)
                )
                SELECT CAST(:query_date AS date) AS date,
                       c.total_capacity,
                       b.cnt AS booked_count,
                       h.cnt AS held_count,
                       GREATEST(c.total_capacity - b.cnt - h.cnt, 0) AS available_capacity
                FROM capacities c
                CROSS JOIN booked b
                CROSS JOIN held h
                """
            )
            result = await self.session.execute(
                sql,
                {
                    "add_on_id": str(add_on_id),
                    "query_date": query_date,
                },
            )
            row = result.mappings().one_or_none()
            if row:
                rows.append(
                    {
                        "date": row.date,
                        "slot_time": None,
                        "total_capacity": row.total_capacity,
                        "booked_count": row.booked_count,
                        "held_count": row.held_count,
                        "available_capacity": row.available_capacity,
                    }
                )

        if self.redis is not None:
            await self.redis.setex(cache_key, 30, json.dumps(rows, default=str))

        return rows

    async def get_addon_availability_range(
        self,
        add_on_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        """Return availability for an add-on across a date range.

        Parameters
        ----------
        add_on_id : uuid.UUID
            Add-on UUID.
        start_date : date
            Start date (inclusive).
        end_date : date
            End date (inclusive).

        Returns
        -------
        list[dict]
            One dict per day/slot in the range.
        """
        if start_date > end_date:
            return []

        cache_key = self._addon_range_cache_key(add_on_id, start_date, end_date)

        if self.redis is not None:
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)

        addon_stmt = select(AddOn).where(AddOn.id == add_on_id)
        result = await self.session.execute(addon_stmt)
        add_on = result.scalar_one_or_none()
        if add_on is None:
            return []

        addon_type = add_on.type
        rows: list[dict] = []

        if addon_type == "package_instance":
            total_capacity = add_on.default_capacity if add_on.default_capacity > 0 else 9999

            sql = text(
                """
                WITH date_series AS (
                    SELECT generate_series(CAST(:start_date AS date), CAST(:end_date AS date), interval '1 day')::date AS d
                ),
                booked AS (
                    SELECT (elem->>'date')::date AS d, COALESCE(SUM((elem->>'quantity')::int), 0) AS cnt
                    FROM inventory_hold ih
                    CROSS JOIN LATERAL jsonb_array_elements(
                        CASE WHEN jsonb_typeof(ih.add_on_holds) = 'array'
                             THEN ih.add_on_holds
                             ELSE '[]'::jsonb
                        END
                    ) AS elem
                    WHERE ih.status = 'committed'
                      AND (elem->>'add_on_id')::uuid = CAST(:add_on_id AS uuid)
                      AND (elem->>'date')::date BETWEEN CAST(:start_date AS date) AND CAST(:end_date AS date)
                    GROUP BY (elem->>'date')::date
                ),
                held AS (
                    SELECT (elem->>'date')::date AS d, COALESCE(SUM((elem->>'quantity')::int), 0) AS cnt
                    FROM inventory_hold ih
                    CROSS JOIN LATERAL jsonb_array_elements(
                        CASE WHEN jsonb_typeof(ih.add_on_holds) = 'array'
                             THEN ih.add_on_holds
                             ELSE '[]'::jsonb
                        END
                    ) AS elem
                    WHERE ih.status = 'active'
                      AND ih.expires_at > NOW()
                      AND (elem->>'add_on_id')::uuid = CAST(:add_on_id AS uuid)
                      AND (elem->>'date')::date BETWEEN CAST(:start_date AS date) AND CAST(:end_date AS date)
                    GROUP BY (elem->>'date')::date
                )
                SELECT ds.d AS date,
                       CAST(:total_capacity AS int) AS total_capacity,
                       COALESCE(b.cnt, 0) AS booked_count,
                       COALESCE(h.cnt, 0) AS held_count,
                       GREATEST(CAST(:total_capacity AS int) - COALESCE(b.cnt, 0) - COALESCE(h.cnt, 0), 0) AS available_capacity
                FROM date_series ds
                LEFT JOIN booked b ON b.d = ds.d
                LEFT JOIN held h ON h.d = ds.d
                ORDER BY ds.d
                """
            )
            result = await self.session.execute(
                sql,
                {
                    "start_date": start_date,
                    "end_date": end_date,
                    "add_on_id": str(add_on_id),
                    "total_capacity": total_capacity,
                },
            )
            rows = [
                {
                    "date": row.date,
                    "slot_time": None,
                    "total_capacity": row.total_capacity,
                    "booked_count": row.booked_count,
                    "held_count": row.held_count,
                    "available_capacity": row.available_capacity,
                }
                for row in result.mappings().all()
            ]

        elif addon_type == "slot":
            sql = text(
                """
                WITH date_series AS (
                    SELECT generate_series(CAST(:start_date AS date), CAST(:end_date AS date), interval '1 day')::date AS d
                ),
                capacities AS (
                    SELECT ac.date, ac.slot_time, ac.total_capacity
                    FROM add_on_capacity ac
                    WHERE ac.add_on_id = CAST(:add_on_id AS uuid)
                      AND ac.date BETWEEN CAST(:start_date AS date) AND CAST(:end_date AS date)
                ),
                booked AS (
                    SELECT (elem->>'date')::date AS d,
                           elem->>'slot_time' AS slot_time,
                           COALESCE(SUM((elem->>'quantity')::int), 0) AS cnt
                    FROM inventory_hold ih
                    CROSS JOIN LATERAL jsonb_array_elements(
                        CASE WHEN jsonb_typeof(ih.add_on_holds) = 'array'
                             THEN ih.add_on_holds
                             ELSE '[]'::jsonb
                        END
                    ) AS elem
                    WHERE ih.status = 'committed'
                      AND (elem->>'add_on_id')::uuid = CAST(:add_on_id AS uuid)
                      AND (elem->>'date')::date BETWEEN CAST(:start_date AS date) AND CAST(:end_date AS date)
                    GROUP BY (elem->>'date')::date, elem->>'slot_time'
                ),
                held AS (
                    SELECT (elem->>'date')::date AS d,
                           elem->>'slot_time' AS slot_time,
                           COALESCE(SUM((elem->>'quantity')::int), 0) AS cnt
                    FROM inventory_hold ih
                    CROSS JOIN LATERAL jsonb_array_elements(
                        CASE WHEN jsonb_typeof(ih.add_on_holds) = 'array'
                             THEN ih.add_on_holds
                             ELSE '[]'::jsonb
                        END
                    ) AS elem
                    WHERE ih.status = 'active'
                      AND ih.expires_at > NOW()
                      AND (elem->>'add_on_id')::uuid = CAST(:add_on_id AS uuid)
                      AND (elem->>'date')::date BETWEEN CAST(:start_date AS date) AND CAST(:end_date AS date)
                    GROUP BY (elem->>'date')::date, elem->>'slot_time'
                )
                SELECT c.date,
                       c.slot_time,
                       c.total_capacity,
                       COALESCE(b.cnt, 0) AS booked_count,
                       COALESCE(h.cnt, 0) AS held_count,
                       GREATEST(c.total_capacity - COALESCE(b.cnt, 0) - COALESCE(h.cnt, 0), 0) AS available_capacity
                FROM capacities c
                LEFT JOIN booked b ON b.d = c.date AND b.slot_time = c.slot_time::text
                LEFT JOIN held h ON h.d = c.date AND h.slot_time = c.slot_time::text
                ORDER BY c.date, c.slot_time
                """
            )
            result = await self.session.execute(
                sql,
                {
                    "start_date": start_date,
                    "end_date": end_date,
                    "add_on_id": str(add_on_id),
                },
            )
            rows = [
                {
                    "date": row.date,
                    "slot_time": row.slot_time,
                    "total_capacity": row.total_capacity,
                    "booked_count": row.booked_count,
                    "held_count": row.held_count,
                    "available_capacity": row.available_capacity,
                }
                for row in result.mappings().all()
            ]

        elif addon_type == "day":
            sql = text(
                """
                WITH date_series AS (
                    SELECT generate_series(CAST(:start_date AS date), CAST(:end_date AS date), interval '1 day')::date AS d
                ),
                capacities AS (
                    SELECT ds.d AS date, COALESCE(SUM(ac.total_capacity), 0) AS total_capacity
                    FROM date_series ds
                    LEFT JOIN add_on_capacity ac ON ac.add_on_id = CAST(:add_on_id AS uuid) AND ac.date = ds.d
                    GROUP BY ds.d
                ),
                booked AS (
                    SELECT (elem->>'date')::date AS d, COALESCE(SUM((elem->>'quantity')::int), 0) AS cnt
                    FROM inventory_hold ih
                    CROSS JOIN LATERAL jsonb_array_elements(
                        CASE WHEN jsonb_typeof(ih.add_on_holds) = 'array'
                             THEN ih.add_on_holds
                             ELSE '[]'::jsonb
                        END
                    ) AS elem
                    WHERE ih.status = 'committed'
                      AND (elem->>'add_on_id')::uuid = CAST(:add_on_id AS uuid)
                      AND (elem->>'date')::date BETWEEN CAST(:start_date AS date) AND CAST(:end_date AS date)
                    GROUP BY (elem->>'date')::date
                ),
                held AS (
                    SELECT (elem->>'date')::date AS d, COALESCE(SUM((elem->>'quantity')::int), 0) AS cnt
                    FROM inventory_hold ih
                    CROSS JOIN LATERAL jsonb_array_elements(
                        CASE WHEN jsonb_typeof(ih.add_on_holds) = 'array'
                             THEN ih.add_on_holds
                             ELSE '[]'::jsonb
                        END
                    ) AS elem
                    WHERE ih.status = 'active'
                      AND ih.expires_at > NOW()
                      AND (elem->>'add_on_id')::uuid = CAST(:add_on_id AS uuid)
                      AND (elem->>'date')::date BETWEEN CAST(:start_date AS date) AND CAST(:end_date AS date)
                    GROUP BY (elem->>'date')::date
                )
                SELECT c.date,
                       c.total_capacity,
                       COALESCE(b.cnt, 0) AS booked_count,
                       COALESCE(h.cnt, 0) AS held_count,
                       GREATEST(c.total_capacity - COALESCE(b.cnt, 0) - COALESCE(h.cnt, 0), 0) AS available_capacity
                FROM capacities c
                LEFT JOIN booked b ON b.d = c.date
                LEFT JOIN held h ON h.d = c.date
                ORDER BY c.date
                """
            )
            result = await self.session.execute(
                sql,
                {
                    "start_date": start_date,
                    "end_date": end_date,
                    "add_on_id": str(add_on_id),
                },
            )
            rows = [
                {
                    "date": row.date,
                    "slot_time": None,
                    "total_capacity": row.total_capacity,
                    "booked_count": row.booked_count,
                    "held_count": row.held_count,
                    "available_capacity": row.available_capacity,
                }
                for row in result.mappings().all()
            ]

        if self.redis is not None:
            await self.redis.setex(cache_key, 30, json.dumps(rows, default=str))

        return rows
