# Partner Role — End-to-End Test Scenarios

**Role Code**: `Partner`  
**Access Level**: Commission-based external agent  
**Precondition**: Admin has created Partner user  

---

## Section P: Authentication

### P-001: Partner Login (P0)
**Steps**:
1. Navigate to `/login`
2. Enter partner email
3. Enter password
4. Click "Sign In"
5. Verify redirect to `/dashboard`
6. Verify sidebar shows: Dashboard, Properties (view), Bookings, Calendar (view)
**Expected**: Partner sees limited nav

### P-002: Partner Cannot Access Admin Panel (P0)
**Steps**:
1. Login as Partner
2. Navigate to `/admin`
3. Verify access denied
**Expected**: Access denied

### P-003: Partner Cannot Access Owner Reports (P1)
**Steps**:
1. Login as Partner
2. Navigate to `/owner`
3. Verify access denied or limited view
**Expected**: Owner reports blocked

---

## Section Q: Dashboard (Partner)

### P-004: Partner Dashboard Shows Commissionable Data (P1)
**Steps**:
1. Navigate to `/dashboard`
2. Verify Today counts
3. Verify commissions visible (if implemented)
**Expected**: Partner-specific metrics

---

## Section R: Bookings (Partner)

### P-005: Partner Can Create Booking (P0)
**Steps**:
1. Navigate to `/bookings/manual`
2. Create booking on behalf of guest
3. Verify partner attribution captured
**Expected**: Booking created with partner_id

### P-006: Partner Can View Their Bookings (P0)
**Steps**:
1. Access `/bookings/{id}`
2. Verify details
3. Verify partner commission shown
**Expected**: Bookings visible

### P-007: Partner Cannot Edit Other's Bookings (P0)
**Steps**:
1. Try to edit booking created by Manager
2. Verify 403 or read-only
**Expected**: Edit restricted

---

## Section S: Cross-Role Boundaries

### P-008: Partner Cannot Create Property (P1)
**Steps**:
1. Navigate to `/properties`
2. Verify "Add Property" hidden
**Expected**: Create restricted

### P-009: Partner Cannot Access OTA Queue (P1)
**Steps**:
1. Navigate to `/ota/queue`
2. Verify access denied
**Expected**: OTA queue blocked

---

## Partner Test Summary

| Section | Scenarios | Pass | Fail | Blocked |
|---------|-----------|------|------|---------|
| Auth | 3 | | | |
| Dashboard | 1 | | | |
| Bookings | 3 | | | |
| Cross-Role | 2 | | | |
| **Total** | **9** | | | |

*Note: Partner role is lightweight in current implementation. Full commission tracking is future scope.*
