# ListingManager Role — End-to-End Test Scenarios

**Role Code**: `ListingManager`  
**Access Level**: Cross-property OTA content management  
**Precondition**: Admin has created ListingManager user  

---

## Section L: Authentication

### L-001: ListingManager Login (P0)
**Steps**:
1. Navigate to `/login`
2. Enter ListingManager email
3. Enter password
4. Click "Sign In"
5. Verify redirect to `/dashboard`
6. Verify sidebar shows: Dashboard, Properties, Calendar, OTA Queue, OTA Mappings
7. Verify sidebar does NOT show: Packages, New Booking, Messages, Owner, Admin
**Expected**: Correct limited navigation

### L-002: ListingManager Cannot Access Admin (P0)
**Steps**:
1. Login as ListingManager
2. Navigate to `/admin`
3. Verify access denied
**Expected**: Admin blocked

### L-003: ListingManager Cannot Access Bookings (P0)
**Steps**:
1. Navigate to `/bookings/manual`
2. Verify access denied
**Expected**: Booking creation blocked

---

## Section M: Properties (ListingManager)

### L-004: ListingManager Can View All Properties (P0)
**Steps**:
1. Navigate to `/properties`
2. Verify property list loads
3. Verify properties from multiple orgs if applicable
**Expected**: Cross-property view

### L-005: ListingManager Can Edit Property Content (P0)
**Steps**:
1. Open property detail
2. Edit description
3. Upload new photos
4. Update amenities
5. Save
**Expected**: Content updated

### L-006: ListingManager Cannot Change Financial Settings (P1)
**Steps**:
1. Open property
2. Verify GSTIN, PAN fields read-only
3. Verify owner contact editable
**Expected**: Financial fields restricted

### L-007: ListingManager Can Edit Room Types (P0)
**Steps**:
1. Open property room types
2. Edit room type description
3. Upload room photos
4. Save
**Expected**: Room type content updated

### L-008: ListingManager Cannot Change Room Rates (P1)
**Steps**:
1. Try to edit base rate
2. Verify field read-only
**Expected**: Rate fields restricted

---

## Section N: Calendar (ListingManager)

### L-009: ListingManager Can View Calendar (P0)
**Steps**:
1. Navigate to `/calendar`
2. Verify month grid loads
3. Switch properties
**Expected**: Calendar accessible

### L-010: ListingManager Cannot Block Dates (P1)
**Steps**:
1. Try to click date cell
2. Verify no block modal or action disabled
**Expected**: Block action restricted

---

## Section O: OTA Queue (ListingManager)

### L-011: ListingManager Can Review OTA Queue (P0)
**Steps**:
1. Navigate to `/ota/queue`
2. Verify items load
3. Filter by source
**Expected**: Queue accessible

### L-012: ListingManager Cannot Confirm OTA Booking (P1)
**Steps**:
1. Find pending item
2. Verify Confirm button hidden or disabled
**Expected**: Confirm action restricted

---

## Section P: OTA Mappings (ListingManager)

### L-013: ListingManager Can View Mappings (P0)
**Steps**:
1. Navigate to `/ota/mappings`
2. Verify table loads
**Expected**: Mappings visible

### L-014: ListingManager Can Create Mapping (P0)
**Steps**:
1. Click "Add Mapping"
2. Fill property, room type, source, listing ID
3. Save
**Expected**: Mapping created

### L-015: ListingManager Can Edit Mapping (P0)
**Steps**:
1. Open existing mapping
2. Change listing ID
3. Save
**Expected**: Mapping updated

### L-016: ListingManager Can Delete Mapping (P0)
**Steps**:
1. Find mapping
2. Click Delete
3. Confirm
**Expected**: Mapping soft-deleted

---

## ListingManager Test Summary

| Section | Scenarios | Pass | Fail | Blocked |
|---------|-----------|------|------|---------|
| Auth | 3 | | | |
| Properties | 5 | | | |
| Calendar | 2 | | | |
| OTA Queue | 2 | | | |
| OTA Mappings | 4 | | | |
| **Total** | **16** | | | |
