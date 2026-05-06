# Guest Role — End-to-End Test Scenarios

**Role Code**: `Guest`  
**Access Level**: Public booking + guest portal  
**Precondition**: Public site active, properties with active room types  

---

## Section G: Public Site

### G-001: Landing Page Loads (P0)
**Steps**:
1. Navigate to `/book`
2. Verify hero section with gradient
3. Verify search bar present
4. Verify trust badges
5. Verify featured properties grid
6. Verify footer
**Expected**: Landing page fully rendered

### G-002: Property Photos on Landing (P1)
**Steps**:
1. Load `/book`
2. Verify property cards show photos
3. Verify fallback when no photos
**Expected**: Photos display, fallback for missing

### G-003: Search Functionality (P0)
**Steps**:
1. Enter location
2. Select check-in date (tomorrow)
3. Select check-out date (day after)
4. Set guests = 2
5. Click Search
6. Verify redirect to `/book/search`
7. Verify results load
8. Verify property cards show price
**Expected**: Search results with pricing

### G-004: Search Empty Results (P1)
**Steps**:
1. Search for location with no properties
2. Verify "No results" message
3. Verify search form still accessible
**Expected**: Graceful empty state

### G-005: Search Invalid Dates (P1)
**Steps**:
1. Select check-in after check-out
2. Click Search
3. Verify validation error
**Expected**: Date validation

---

## Section H: Booking Flow

### G-006: Select Room and Book (P0)
**Precondition**: Search results exist
**Steps**:
1. On search results, click "Book Now" on a room card
2. Verify redirect to `/book/flow`
3. Verify pre-filled dates and guests
4. Fill guest name, email, phone
5. Enter promo code (optional)
6. Click "Proceed to Payment"
7. Verify Razorpay checkout opens
**Expected**: Booking flow reaches payment

### G-007: Payment Success (P0)
**Steps**:
1. Complete Razorpay payment (test mode)
2. Verify redirect to `/book/confirm`
3. Verify booking reference displayed
4. Verify booking details shown
5. Verify "Download Invoice" button
**Expected**: Booking confirmed

### G-008: Payment Failure & Retry (P0)
**Steps**:
1. In payment, use failing test card
2. Verify failure message
3. Click "Retry Payment"
4. Use valid test card
5. Verify success
**Expected**: Retry works

### G-009: Booking Conflict During Flow (P1)
**Steps**:
1. Start booking for available room
2. In another session, book same room
3. Complete payment in first session
4. Verify 409 conflict with alternatives
**Expected**: Conflict handled gracefully

### G-010: Booking Confirmation Email (P2)
**Steps**:
1. Complete booking
2. Check email (if configured)
3. Verify confirmation email received
**Expected**: Email sent

---

## Section I: Guest Portal

### G-011: Guest Signup (P0)
**Steps**:
1. Navigate to `/guest/signup`
2. Fill name, email, phone, password
3. Submit
4. Verify redirect to guest dashboard
5. Verify welcome message
**Expected**: Account created and logged in

### G-012: Guest Login (P0)
**Steps**:
1. Navigate to `/guest/login`
2. Enter email and password
3. Submit
4. Verify redirect to `/guest`
**Expected**: Guest logged in

### G-013: Guest Views Bookings (P0)
**Steps**:
1. Login as guest
2. Navigate to `/guest`
3. Verify "My Bookings" card
4. Verify upcoming booking shown
5. Verify past bookings listed
**Expected**: Own bookings visible

### G-014: Guest Views Booking Detail (P0)
**Steps**:
1. Click on a booking
2. Verify full details
3. Verify payment status
**Expected**: Detail view accessible

### G-015: Guest Modifies Booking (P1)
**Steps**:
1. Open booking detail
2. Click "Modify"
3. Change dates
4. Verify modification policy
5. Confirm changes
**Expected**: Modification processed

### G-016: Guest Cancels Booking (P0)
**Steps**:
1. Open booking
2. Click "Cancel"
3. Verify cancellation policy
4. Verify refund amount
5. Confirm cancellation
6. Verify status updated
**Expected**: Cancellation with refund

### G-017: Guest Retry Failed Payment (P0)
**Steps**:
1. Have booking with failed payment
2. Click "Retry Payment"
3. Complete payment
4. Verify status updated
**Expected**: Payment succeeds

---

## Section J: Guest Security

### G-018: Guest Cannot Access Staff Pages (P0)
**Steps**:
1. Login as guest
2. Navigate to `/dashboard`
3. Verify redirect to `/login`
4. Navigate to `/admin`
5. Verify access denied
**Expected**: Staff routes blocked

### G-019: Guest Cannot See Other Guest Bookings (P0)
**Steps**:
1. Login as Guest A
2. Try to access `/bookings/{Guest-B-booking-id}`
3. Verify 403 or not found
**Expected**: Booking isolation enforced

---

## Guest Test Summary

| Section | Scenarios | Pass | Fail | Blocked |
|---------|-----------|------|------|---------|
| Public Site | 5 | | | |
| Booking Flow | 5 | | | |
| Guest Portal | 7 | | | |
| Security | 2 | | | |
| **Total** | **19** | | | |
