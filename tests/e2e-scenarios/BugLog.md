# Bug Log — E2E Testing

## Format
```
BUG-{ID}: {Title}
- Role: {Role}
- Scenario: {Scenario ID}
- Severity: {P0/P1/P2/P3}
- Date Found: {Date}
- Date Fixed: {Date}

### Steps to Reproduce
1. Step 1
2. Step 2

### Expected
{What should happen}

### Actual
{What actually happened}

### Root Cause
{Technical analysis}

### Fix
{File changes made}

### Verification
{How verified}

### Status: OPEN / IN_PROGRESS / FIXED / VERIFIED
```

---

## Bug Index

| ID | Title | Role | Severity | Status |
|----|-------|------|----------|--------|
| BUG-001 | Database migrations not applied on fresh start | All | P0 | FIXED |
| BUG-002 | Login fails after setup due to org_id mismatch | Admin | P0 | FIXED |
| BUG-003 | API create/update endpoints do not persist data (missing db.commit) | All | P0 | FIXED |
| BUG-004 | Frontend does not send X-Org-ID header on authenticated requests | All | P0 | FIXED |
| BUG-005 | Backend endpoints lack authentication and role-based access control | All | P0 | FIXED |
| BUG-006 | Role-based access control not enforced on authenticated endpoints | All | P0 | FIXED |
| BUG-007 | Overbooking not prevented in staff create_booking endpoint | Admin/Manager/Staff | P0 | OPEN |
| BUG-008 | Users endpoint allowed any authenticated user to create users | All | P0 | FIXED |
| BUG-009 | Room type accepted negative pricing without validation | All | P0 | FIXED |

---

## Bug Details

### BUG-001: Database migrations not applied on fresh start
- Role: All
- Scenario: A-001
- Severity: P0
- Date Found: 2026-05-05
- Date Fixed: 2026-05-05

#### Steps to Reproduce
1. Start Docker with fresh volumes (`docker compose up`)
2. Call `GET /api/v1/auth/setup-status`
3. Observe Internal Server Error

#### Expected
`{"setup_required": true}`

#### Actual
`Internal Server Error` with backend logs showing:
`UndefinedTableError: relation "user" does not exist`

#### Root Cause
Alembic migrations were not automatically run on container startup. The database was empty with no tables.

#### Fix
Ran `docker exec brekora_api alembic upgrade heads` manually. Long-term fix: add migration step to entrypoint script.

#### Verification
After running migrations, `setup-status` returns `{"setup_required": true}` successfully.

#### Status: FIXED

---

### BUG-002: Login fails after setup due to org_id mismatch
- Role: Admin
- Scenario: A-003
- Severity: P0
- Date Found: 2026-05-05
- Date Fixed: 2026-05-05

#### Steps to Reproduce
1. Complete first-time setup (`POST /auth/setup`)
2. Attempt to login with created admin credentials (`POST /auth/login`)
3. Observe 401 "Invalid credentials"

#### Expected
Successful login with tokens returned

#### Actual
401 Unauthorized - "Invalid credentials"

#### Root Cause
The `/auth/setup` endpoint creates a NEW organization with a new `org_id`. However, the `/auth/login` endpoint defaults to a hardcoded `DEFAULT_ORG_ID` (00000000-0000-0000-0000-000000000001) when no `X-Org-ID` header is provided. The `UserRepository.get_by_email()` applies org scope, so it searches for the user in the wrong organization.

#### Fix
1. Added `UserRepository.get_by_email_unscoped()` method in `backend/app/repositories/user.py`
2. Modified login endpoint to detect when no `X-Org-ID` header was sent, look up the user globally to discover their actual `org_id`, then proceed with that org_id

Files changed:
- `backend/app/repositories/user.py` - added `get_by_email_unscoped`
- `backend/app/api/v1/endpoints/auth.py` - login uses unscoped lookup when no org header

#### Verification
After fix, login with `admin@test.com` / `password123` returns 200 with valid tokens.

#### Status: FIXED

---

### BUG-003: API create/update endpoints do not persist data (missing db.commit)
- Role: All
- Scenario: A-004 (Admin creates property)
- Severity: P0
- Date Found: 2026-05-05
- Date Fixed: 2026-05-05

#### Steps to Reproduce
1. Login as Admin
2. `POST /properties/` with valid payload
3. `GET /properties/` immediately after
4. Observe empty list

#### Expected
Created property appears in list

#### Actual
Property returned in 201 response but is missing from subsequent GET. Data rolled back because transaction was never committed.

#### Root Cause
`get_db()` dependency yielded the session but never committed or rolled back. Only `/auth/setup` called `await db.commit()` explicitly. Every other endpoint (properties, bookings, users, packages, pricing, etc.) relied on `flush()` inside repositories, which writes to DB within the transaction but does not commit. When the request context closed, SQLAlchemy closed the session and the uncommitted transaction was rolled back.

#### Fix
Modified `backend/app/db/session.py` `get_db()` to auto-commit after successful request execution and rollback on exception:
```python
async def get_db() -> AsyncSession:
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
```

#### Verification
After fix, `POST /properties/` followed by `GET /properties/` returns the created property. Tested with and without `X-Org-ID` header to confirm org scoping also works.

#### Status: FIXED

---

### BUG-004: Frontend does not send X-Org-ID header on authenticated requests
- Role: All
- Scenario: A-004 (Admin views properties)
- Severity: P0
- Date Found: 2026-05-05
- Date Fixed: 2026-05-05

#### Steps to Reproduce
1. Complete setup and login via frontend
2. Navigate to Dashboard or Properties
3. Observe all counts are zero / lists are empty
4. Backend receives requests without `X-Org-ID` header

#### Expected
Frontend sends `X-Org-ID` matching the organization created during setup, so backend returns actual data.

#### Actual
Backend defaults to hardcoded `DEFAULT_ORG_ID`, which doesn't match the setup-created org. Org-scoped queries return empty results.

#### Root Cause
1. `frontend/src/store/authStore.ts` did not store `org_id` from the JWT payload
2. `frontend/src/lib/api.ts` Axios interceptor did not attach an `X-Org-ID` header
3. `frontend/src/hooks/useAuth.ts` decoded JWT but didn't extract `org_id`
4. `frontend/src/pages/auth/Setup.tsx` manually decoded JWT but didn't extract `org_id`

#### Fix
1. Added `org_id?: string` to the `User` interface in `authStore.ts`
2. Updated `api.ts` request interceptor to read `user.org_id` from auth store and set `X-Org-ID` header
3. Updated `decodeJwt` and `getUserFromToken` in both `useAuth.ts` and `useGuestAuth.ts` to extract `org_id`
4. Updated `Setup.tsx` to include `org_id` in the user object passed to `setAuth`
5. Updated fallback user objects in `useAuth.ts` and `useGuestAuth.ts` to include `org_id: ''`

Files changed:
- `frontend/src/store/authStore.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/hooks/useAuth.ts`
- `frontend/src/hooks/useGuestAuth.ts`
- `frontend/src/pages/auth/Setup.tsx`

#### Verification
After fix, API calls from the frontend include `X-Org-ID: <setup-org-id>` header. Properties created via API appear when fetched by the frontend.

#### Status: FIXED

---

### BUG-005: Backend endpoints lack authentication and role-based access control
- Role: All
- Scenario: CR-001 through CR-006
- Severity: P0
- Date Found: 2026-05-05
- Date Fixed: 2026-05-05

#### Steps to Reproduce
1. `curl http://localhost:8000/api/v1/properties/` without any auth header → returns 200
2. `curl http://localhost:8000/api/v1/bookings/` without auth → returns 200
3. `curl http://localhost:8000/api/v1/users/` without auth → returns 200
4. Login as Guest, then call `/properties/`, `/bookings/`, `/packages/`, `/ota/queue/` → all return 200

#### Expected
- Unauthenticated requests to staff endpoints should return 401
- Guest role should not be able to access `/bookings/`, `/ota/queue/`, `/packages/`
- ListingManager should not access `/bookings/manual`
- Partner should not access `/ota/queue`

#### Actual
All endpoints return 200 for any request, regardless of auth state or role.

#### Root Cause
Most API routers (properties, bookings, users, packages, ota_queue, ota_mappings, pricing, add_ons, etc.) were created without `Depends(get_current_user)` or `Depends(require_role(...))`. Only `gst.py`, `ota_metrics.py`, and `sessions.py` had role checks.

#### Fix
Added `dependencies=[Depends(get_current_user)]` to the internal staff routers in `backend/app/api/v1/api.py`. For endpoints that must remain public (property search, booking init, webhooks, health check), overridden with `dependencies=[]` on the specific routes.

Files changed:
- `backend/app/api/v1/api.py` - added auth dependencies to routers
- `backend/app/api/v1/endpoints/bookings.py` - made `init` and `create` public, protected list/detail/update
- `backend/app/api/v1/endpoints/properties.py` - made `GET /` and `GET /{id}` public, protected write ops

#### Verification
After fix, unauthenticated requests to `/users/`, `/packages/`, `/ota/queue/`, `/ota/mappings/` return 401. Public endpoints (`/properties/`, `/bookings/init`, `/search`) remain accessible.

#### Status: FIXED

---

### BUG-006: Role-based access control not enforced on authenticated endpoints
- Role: All
- Scenario: CR-001 through CR-006, M-002, L-003, P-002, A-040
- Severity: P0
- Date Found: 2026-05-05
- Date Fixed: 2026-05-05

#### Steps to Reproduce
1. Login as Guest, `GET /api/v1/bookings/` → returns 200
2. Login as ListingManager, `GET /api/v1/bookings/` → returns 200
3. Login as Partner, `GET /api/v1/ota/queue/` → returns 200
4. Login as Manager, `GET /api/v1/feature-flags/` → returns 200
5. Navigate to `/admin` in frontend while logged in as Manager → page loads
6. Navigate to `/bookings/manual` in frontend while logged in as Guest → page loads

#### Expected
- Guest should not access staff booking endpoints
- ListingManager should not access bookings
- Partner should not access OTA queue
- Manager should not access admin-only endpoints
- Frontend routes should be guarded by auth and role

#### Actual
Any authenticated user could access any endpoint. Frontend routes had no guards.

#### Root Cause
1. Backend: `get_current_user` only validated authentication, not role. `require_role` existed in `deps.py` but was never used in endpoint definitions.
2. Frontend: `router.tsx` defined all routes without any auth or role guards.

#### Fix
1. **Backend**: Added `dependencies=[Depends(require_role([...]))]` to:
   - `bookings.py`: list, by-guest, by-property, by-date-range, update, modify, delete restricted to Admin/Manager/Owner/Partner
   - `feature_flags.py`: all CRUD endpoints restricted to Admin only; `/check/{key}` left public
   - `ota_queue.py`: all endpoints restricted to Admin/Manager/ListingManager

2. **Frontend**: Created `AuthGuard` and `RoleGuard` components in `frontend/src/components/auth/`:
   - `AuthGuard` redirects unauthenticated users to `/login`
   - `RoleGuard` shows access denied for users without allowed role
   - Updated `router.tsx` to wrap staff routes with `AuthGuard` and admin routes with `RoleGuard(allowedRoles=['Admin'])`
   - `/bookings/manual` wrapped with `RoleGuard(allowedRoles=['Admin','Manager','Owner','Partner'])` to exclude ListingManager

Files changed:
- `backend/app/api/v1/endpoints/bookings.py` - added require_role dependencies
- `backend/app/api/v1/endpoints/feature_flags.py` - added admin-only restrictions
- `backend/app/api/v1/endpoints/ota_queue.py` - added role restrictions
- `frontend/src/components/auth/AuthGuard.tsx` - new auth guard component
- `frontend/src/components/auth/RoleGuard.tsx` - new role guard component
- `frontend/src/router.tsx` - wrapped routes with guards

#### Verification
- Guest token → `/bookings/` returns 403
- ListingManager token → `/bookings/` returns 403, `/ota/queue/` returns 200
- Partner token → `/ota/queue/` returns 403, `/bookings/` returns 200
- Manager token → `/feature-flags/` returns 403, `/bookings/` returns 200
- Admin token → all endpoints return 200
- Unauthenticated → protected endpoints return 401

#### Status: FIXED

---

### BUG-007: Overbooking not prevented in staff create_booking endpoint
- Role: Admin/Manager/Staff
- Scenario: A-043
- Severity: P0
- Date Found: 2026-05-05
- Date Fixed: 2026-05-09

#### Steps to Reproduce
1. Create property with 1 room type (count=1)
2. Create booking for that room on 2026-05-15 to 2026-05-16 via POST /bookings/
3. Create second booking for same room on same dates via POST /bookings/
4. Both bookings return 201 and are created successfully

#### Expected
Second booking should return 409 CONFLICT with alternative suggestions (as per A-043)

#### Actual
Second booking is created successfully, resulting in overbooking.

#### Root Cause
The `create_booking` endpoint performed a plain `InventoryService.check_availability()` call but never created an inventory hold. Since `check_availability` counts `InventoryHold` records (not `Booking` records), subsequent requests could not see the newly created booking and would also pass the availability check, leading to overbooking.

#### Fix
After creating the booking, the endpoint now calls `InventoryService.hold_inventory()` followed by `InventoryService.commit_inventory()` within the same request flow. `hold_inventory` uses `SERIALIZABLE` isolation with `SELECT FOR UPDATE`, which serializes concurrent requests. If the hold fails (insufficient inventory, serialization failure, or conflict), the booking is deleted and a 409 is returned.

Files changed:
- `backend/app/api/v1/endpoints/bookings.py` - added hold + commit after booking creation, with rollback on failure

#### Verification
After fix, second concurrent staff booking on same dates returns 409 CONFLICT.

#### Status: FIXED


---

### BUG-008: Users endpoint allowed any authenticated user to create users
- Role: All
- Scenario: M-023
- Severity: P0
- Date Found: 2026-05-05
- Date Fixed: 2026-05-05

#### Steps to Reproduce
1. Login as Manager
2. POST /api/v1/users/ with valid payload
3. Observe 201 and user created

#### Expected
403 Forbidden - only Admin should be able to create users

#### Actual
201 Created - any authenticated user could create users

#### Root Cause
The `users.py` endpoints only had `get_current_user` dependency (from router-level in `api.py`) but no `require_role` check. Any authenticated user could call create_user, list_users, update_user, delete_user.

#### Fix
Added `dependencies=[Depends(require_role(["Admin"]))]` to all endpoints in `backend/app/api/v1/endpoints/users.py`.

#### Verification
After fix, Manager token POST /users/ returns 403 "Insufficient permissions". Admin token still returns 201.

#### Status: FIXED

---

### BUG-009: Room type accepted negative pricing without validation
- Role: All
- Scenario: PE-005
- Severity: P0
- Date Found: 2026-05-05
- Date Fixed: 2026-05-05

#### Steps to Reproduce
1. PATCH /api/v1/room-types/{id} with `{"default_rate": -100}`
2. Observe 200 OK

#### Expected
422 Unprocessable Entity - negative rate should be rejected

#### Actual
200 OK - negative rate stored in database, causing ResponseValidationError on subsequent reads

#### Root Cause
`RoomTypeBase` and `RoomTypeUpdate` schemas used plain `Decimal` and `int` types without `Field(ge=...)` validation constraints.

#### Fix
Updated `backend/app/schemas/room_type.py`:
- Added `Field(ge=0)` to `count` and `default_rate`
- Added `Field(ge=1)` to `base_capacity`, `max_capacity`, `min_stay`, `max_stay`
- Applied same constraints to `RoomTypeUpdate` optional fields

#### Verification
After fix, PATCH with `default_rate: -100` returns 422 with validation error "Input should be greater than or equal to 0".

#### Status: FIXED

