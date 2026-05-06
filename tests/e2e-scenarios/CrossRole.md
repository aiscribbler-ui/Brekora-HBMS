# Cross-Role & Edge Case Test Scenarios

## Overview
Tests that verify boundaries between roles, system-wide features, and edge cases.

---

## Section CR: Role Permission Matrix

### CR-001: Admin Can Access Everything (P0)
**Steps**:
1. Login as Admin
2. Access each route: /dashboard, /properties, /calendar, /packages, /ota/queue, /ota/mappings, /bookings/manual, /bookings/{id}, /owner, /admin, /messages
3. Verify all load successfully
**Expected**: 100% access

### CR-002: Manager Cannot Access Admin (P0)
**Steps**:
1. Login as Manager
2. Access /admin
3. Verify 403
**Expected**: Blocked

### CR-003: Guest Cannot Access Any Staff Route (P0)
**Steps**:
1. Login as Guest
2. Access /dashboard, /properties, /calendar, /ota/queue
3. Verify all redirect to /login or show access denied
**Expected**: All blocked

### CR-004: ListingManager Cannot Access Bookings (P0)
**Steps**:
1. Login as ListingManager
2. Access /bookings/manual
3. Verify blocked
**Expected**: Blocked

### CR-005: Partner Cannot Access OTA Queue (P0)
**Steps**:
1. Login as Partner
2. Access /ota/queue
3. Verify blocked
**Expected**: Blocked

### CR-006: Unauthenticated User Redirect (P0)
**Steps**:
1. Clear localStorage
2. Access /dashboard
3. Verify redirect to /login
4. Access /guest
5. Verify redirect to /guest/login
**Expected**: Auth redirects work

---

## Section SE: Session & Token Security

### SE-001: Expired Token Rejection (P0)
**Steps**:
1. Login
2. Wait for token to expire (or mock expired token)
3. Make API request
4. Verify 401
5. Verify redirect to /login
**Expected**: Expired token rejected

### SE-002: Token Tampering (P0)
**Steps**:
1. Modify JWT payload
2. Make request
3. Verify 401
**Expected**: Invalid signature rejected

### SE-003: Refresh Token Rotation (P1)
**Steps**:
1. Use refresh token
2. Verify new refresh token issued
3. Try to use old refresh token
4. Verify 401
**Expected**: Refresh token rotation works

### SE-004: Concurrent Session Management (P1)
**Steps**:
1. Login in Tab 1
2. Login in Tab 2
3. Check session list
4. Verify both sessions tracked
**Expected**: Concurrent sessions managed

---

## Section DI: Data Integrity

### DI-001: No Orphaned Bookings on Property Delete (P0)
**Steps**:
1. Create property
2. Create booking for property
3. Archive property
4. Verify booking still exists with valid property reference
**Expected**: Soft delete preserves relationships

### DI-002: Inventory Consistency (P0)
**Steps**:
1. Check availability = 5
2. Book 2 rooms
3. Check availability = 3
4. Cancel booking
5. Check availability = 5
**Expected**: Inventory matches

### DI-003: Booking Modification Audit Trail (P1)
**Steps**:
1. Create booking
2. Modify dates
3. Check modification_log
4. Verify entry contains old/new values
**Expected**: Audit trail maintained

### DI-004: Payment-Booking Consistency (P0)
**Steps**:
1. Create booking
2. Make payment
3. Verify payment state on booking
4. Verify booking status updated
**Expected**: Payment and booking in sync

---

## Section PE: Performance & Edge Cases

### PE-001: Large Dataset Pagination (P1)
**Steps**:
1. Create 1000 bookings
2. Load /bookings list
3. Verify pagination
4. Verify page loads in <2s
**Expected**: Paginated, fast

### PE-002: Special Characters in Names (P2)
**Steps**:
1. Create property with name "Test <> & Property"
2. Verify displays correctly
3. Verify no XSS
**Expected**: Special chars handled

### PE-003: Unicode Support (P2)
**Steps**:
1. Create guest with name "Raj मैं हूँ"
2. Verify displays correctly
**Expected**: Unicode supported

### PE-004: Very Long Input (P2)
**Steps**:
1. Enter 5000 char string in description
2. Save
3. Verify stored correctly
4. Verify UI handles overflow
**Expected**: Long input handled

### PE-005: Negative Pricing Attempt (P0)
**Steps**:
1. Try to set room rate = -100
2. Verify validation rejects
**Expected**: Negative values blocked

---

## Section IN: Integration Points

### IN-001: Gmail OTA Parsing (P1)
**Steps**:
1. Configure Gmail OAuth
2. Send test booking email
3. Verify email queued
4. Verify parser extracts details
5. Verify booking appears in queue
**Expected**: Email parsed successfully

### IN-002: Razorpay Webhook (P0)
**Steps**:
1. Create booking
2. Initiate payment
3. Complete payment
4. Verify webhook received
5. Verify booking confirmed
**Expected**: Webhook processes correctly

### IN-003: Redis Health (P1)
**Steps**:
1. Check Redis connection
2. Verify rate limiting works
3. Verify session storage
4. Verify cache invalidation
**Expected**: Redis functional

---

## Section RE: Regression Scenarios

### RE-001: After Fix — Setup Flow (P0)
**Steps**:
1. Fresh database
2. Complete setup
3. Verify admin created
4. Verify can login
5. Verify all roles seeded
**Expected**: Setup fully working

### RE-002: After Fix — OTA Mappings Navigation (P0)
**Steps**:
1. From dashboard, click "Edit OTA Mapping"
2. Verify navigates to /ota/mappings
3. Create mapping
4. Verify persists
**Expected**: Navigation and CRUD work

### RE-003: After Fix — Message Guest (P0)
**Steps**:
1. From dashboard, click "Message Guest"
2. Verify navigates to /messages
3. Select booking
4. Compose message
5. Verify WhatsApp link works
**Expected**: Messaging flow works

---

## Cross-Role Test Summary

| Section | Scenarios | Pass | Fail | Blocked |
|---------|-----------|------|------|---------|
| Permission Matrix | 6 | | | |
| Session Security | 4 | | | |
| Data Integrity | 4 | | | |
| Performance | 5 | | | |
| Integration | 3 | | | |
| Regression | 3 | | | |
| **Total** | **25** | | | |
