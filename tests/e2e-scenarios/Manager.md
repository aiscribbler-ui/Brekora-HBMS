# Manager Role — End-to-End Test Scenarios

**Role Code**: `Manager`  
**Access Level**: Day-to-day operations  
**Precondition**: Manager user exists, properties exist, admin has set up system  

---

## Section M: Authentication

### M-001: Manager Login (P0)
**Precondition**: Admin has created Manager user via User Management
**Steps**:
1. Navigate to `/login`
2. Enter manager email
3. Enter password
4. Click "Sign In"
5. Verify redirect to `/dashboard`
6. Verify sidebar shows: Dashboard, Properties, Calendar, Packages, OTA Queue, New Booking, Messages, Owner
7. Verify sidebar does NOT show: Admin
**Expected**: Manager sees correct limited nav

### M-002: Manager Cannot Access Admin Panel (P0)
**Steps**:
1. Login as Manager
2. Navigate directly to `/admin`
3. Verify "Access Denied" page
4. Verify redirect to home after 3 seconds
**Expected**: Access denied

### M-003: Manager Cannot Access Setup (P0)
**Steps**:
1. Login as Manager
2. Navigate to `/setup`
3. Verify redirect to `/login`
**Expected**: Setup page blocked

---

## Section N: Dashboard (Manager View)

### M-004: Manager Dashboard Shows Only Assigned Properties (P1)
**Steps**:
1. Login as Manager assigned to Property A only
2. Navigate to `/dashboard`
3. Verify Properties list shows only Property A
4. Verify Today counts reflect Property A only
**Expected**: Scoped to assigned properties

### M-005: Manager Quick Actions Work (P0)
**Steps**:
1. Click each Quick Action button
2. Verify all navigate correctly
**Expected**: All actions accessible

---

## Section O: Property Management (Manager)

### M-006: Manager Can View Properties (P0)
**Steps**:
1. Navigate to `/properties`
2. Verify property list loads
3. Verify "Add Property" button visible
**Expected**: Full property list accessible

### M-007: Manager Can Create Property (P1)
**Steps**:
1. Click "Add Property"
2. Fill all required fields
3. Submit
4. Verify property created
**Expected**: Manager can create properties

### M-008: Manager Cannot Delete Property (P1)
**Steps**:
1. Open property detail
2. Verify "Delete" button hidden or disabled
3. Try to call DELETE API directly
4. Verify 403 response
**Expected**: Delete restricted

### M-009: Manager Can Edit Room Type (P0)
**Steps**:
1. Open property room types
2. Edit existing room type
3. Change rate
4. Save
**Expected**: Edit succeeds

---

## Section P: Calendar (Manager)

### M-010: Manager Can Block Dates (P0)
**Steps**:
1. Navigate to `/calendar`
2. Click date cell
3. Block date with reason
4. Verify block persists
**Expected**: Block created

### M-011: Manager Can See All Property Calendars (P1)
**Steps**:
1. Switch property in calendar selector
2. Verify grid updates
**Expected**: All properties accessible

---

## Section Q: Bookings (Manager)

### M-012: Manager Can Create Manual Booking (P0)
**Steps**:
1. Navigate to `/bookings/manual`
2. Complete full booking form
3. Submit
4. Verify booking created
**Expected**: Booking created successfully

### M-013: Manager Can View All Bookings (P0)
**Steps**:
1. Access booking detail `/bookings/{id}`
2. Verify details load
**Expected**: All bookings visible

### M-014: Manager Can Edit Booking (P0)
**Steps**:
1. Open booking
2. Click Edit
3. Change guest name
4. Save
**Expected**: Edit succeeds

### M-015: Manager Can Cancel Booking (P0)
**Steps**:
1. Open confirmed booking
2. Click Cancel
3. Provide reason
4. Confirm
**Expected**: Booking cancelled

### M-016: Manager Cannot See Financial Summary (P2)
**Steps**:
1. Navigate to `/owner`
2. Verify if P&L data visible
3. Verify if payout data restricted
**Expected**: May see summary but not detailed financials

---

## Section R: OTA Queue (Manager)

### M-017: Manager Can Review OTA Queue (P0)
**Steps**:
1. Navigate to `/ota/queue`
2. Verify items load
3. Filter by source
**Expected**: Queue accessible

### M-018: Manager Can Confirm OTA Booking (P0)
**Steps**:
1. Find pending item
2. Click Confirm
3. Verify booking created
**Expected**: Booking imported

### M-019: Manager Can Reject OTA Booking (P0)
**Steps**:
1. Find item
2. Click Reject
3. Enter reason
4. Confirm
**Expected**: Booking rejected

---

## Section S: Packages (Manager)

### M-020: Manager Can Create Package (P1)
**Steps**:
1. Navigate to `/packages`
2. Click "Create Package"
3. Fill details
4. Save
**Expected**: Package created

### M-021: Manager Can Edit Package (P1)
**Steps**:
1. Open existing package
2. Modify pricing rule
3. Save
**Expected**: Package updated

---

## Section T: Messages (Manager)

### M-022: Manager Can Message Guest (P1)
**Steps**:
1. Navigate to `/messages`
2. Select booking
3. Compose message
4. Send via WhatsApp
**Expected**: Message sent

---

## Section U: Cross-Role Boundaries

### M-023: Manager Tries to Invite User (P0)
**Steps**:
1. Navigate to `/admin/user-management`
2. Verify access denied
**Expected**: Cannot access user management

### M-024: Manager Tries to Toggle Feature Flags (P0)
**Steps**:
1. Navigate to `/admin/feature-flags`
2. Verify access denied
**Expected**: Cannot access feature flags

---

## Manager Test Summary

| Section | Scenarios | Pass | Fail | Blocked |
|---------|-----------|------|------|---------|
| Auth | 3 | | | |
| Dashboard | 2 | | | |
| Properties | 4 | | | |
| Calendar | 2 | | | |
| Bookings | 5 | | | |
| OTA Queue | 3 | | | |
| Packages | 2 | | | |
| Messages | 1 | | | |
| Cross-Role | 2 | | | |
| **Total** | **24** | | | |
