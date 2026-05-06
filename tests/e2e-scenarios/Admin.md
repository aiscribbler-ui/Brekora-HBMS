# Admin Role — End-to-End Test Scenarios

**Role Code**: `Admin`  
**Access Level**: Full system access  
**Precondition**: Admin user exists and is logged in  

---

## Section A: Authentication & Setup

### A-001: First-Time Setup Flow (P0)
**Precondition**: Fresh database with zero users
**Steps**:
1. Navigate to `http://localhost/`
2. Verify redirect to `/setup`
3. Observe "Welcome to Brekora" setup form
4. Leave all fields empty, click "Complete Setup"
5. Verify validation errors on all fields
6. Fill Organization Name = "Test Org"
7. Fill Admin Full Name = "Test Admin"
8. Fill Admin Email = "invalid-email"
9. Fill Password = "123", Confirm Password = "123"
10. Click "Complete Setup"
11. Verify email format validation error
12. Fill Admin Email = "admin@test.com"
13. Fill Password = "password123", Confirm Password = "different"
14. Click "Complete Setup"
15. Verify "Passwords do not match" error
16. Fill Confirm Password = "password123"
17. Click "Complete Setup"
18. Verify redirect to `/dashboard`
19. Verify admin token in localStorage (`brekora-auth`)
20. Verify JWT payload contains role="Admin"
**Expected**: Setup succeeds, user is logged in, redirected to dashboard

### A-002: Setup Guard — Already Completed (P0)
**Precondition**: Setup is already done (A-001 complete)
**Steps**:
1. Navigate directly to `/setup`
2. Verify redirect to `/login`
3. Open browser console, verify no 403 errors
**Expected**: Redirected to login page

### A-003: Admin Login with Valid Credentials (P0)
**Precondition**: Admin user exists
**Steps**:
1. Navigate to `/login`
2. Enter valid admin email
3. Enter valid password
4. Click "Sign In"
5. Verify redirect to `/dashboard`
6. Verify sidebar shows all nav items including Admin
**Expected**: Successful login, full sidebar visible

### A-004: Admin Login with Invalid Password (P0)
**Steps**:
1. Navigate to `/login`
2. Enter valid admin email
3. Enter invalid password
4. Click "Sign In"
5. Verify error message displayed
6. Repeat 4 more times with wrong password
7. Verify rate limit kicks in (429 error)
**Expected**: 401 for first 4, then 429 for rate limit

### A-005: Admin Logout (P0)
**Steps**:
1. Login as admin
2. Click "Logout" in header
3. Verify redirect to `/login`
4. Verify localStorage cleared
5. Try to access `/dashboard` directly
6. Verify redirect to `/login`
**Expected**: Full logout, auth state cleared, protected routes blocked

### A-006: Token Refresh (P1)
**Steps**:
1. Login as admin
2. Wait for access token to approach expiry
3. Verify token refresh API called automatically
4. Verify new access token stored
**Expected**: Seamless refresh, no user interruption

### A-007: Concurrent Session Limit (P1)
**Steps**:
1. Login as admin in Browser Tab 1
2. Login as same admin in Browser Tab 2 (incognito)
3. Verify if session limit enforced
4. Return to Tab 1, perform action
**Expected**: Depending on config, either limit enforced or both sessions valid

---

## Section B: Dashboard

### A-008: Dashboard Loads Real Data (P0)
**Steps**:
1. Login as admin
2. Navigate to `/dashboard`
3. Verify all widgets present: Today, Week Summary, Open Tasks, Quick Actions, Properties
4. Verify data is not all zeros (if backend has data)
5. Verify auto-refresh indicator or timer
**Expected**: Dashboard renders with real counts

### A-009: Dashboard Refresh Button (P1)
**Steps**:
1. On dashboard, click "Refresh"
2. Verify loading state
3. Verify data updates
4. Verify no duplicate network requests
**Expected**: Single refresh, data updates

### A-010: Dashboard Quick Actions Navigation (P0)
**Steps**:
1. Click "Create Booking" → verify `/bookings/manual`
2. Click "Block Dates" → verify `/calendar`
3. Click "Message Guest" → verify `/messages`
4. Click "Review OTA Queue" → verify `/ota/queue`
5. Click "Edit OTA Mapping" → verify `/ota/mappings`
**Expected**: All buttons navigate to correct routes

---

## Section C: Property Management

### A-011: Create New Property (P0)
**Steps**:
1. Navigate to `/properties`
2. Click "Add Property"
3. Fill name, address, GSTIN, PAN, owner contact
4. Upload property photos
5. Add amenities
6. Set check-in/check-out times
7. Submit form
8. Verify property appears in list
9. Verify property detail page loads
**Expected**: Property created with all fields

### A-012: Edit Property (P0)
**Steps**:
1. Open existing property detail
2. Click "Edit"
3. Change property name
4. Save changes
5. Verify list and detail reflect changes
**Expected**: Property updated successfully

### A-013: Archive Property (P1)
**Steps**:
1. Open property detail
2. Click "Archive"
3. Confirm dialog
4. Verify property disappears from active list
5. Verify property still accessible via direct URL but marked archived
**Expected**: Soft delete, data preserved

### A-014: Add Room Type (P0)
**Steps**:
1. Open property detail
2. Navigate to Room Types
3. Click "Add Room Type"
4. Fill name, count, base capacity, max capacity, rate
5. Upload room photos
6. Set min/max stay
7. Save
8. Verify room type appears in list
**Expected**: Room type created successfully

### A-015: Edit Room Type (P0)
**Steps**:
1. Open room type detail
2. Change base rate
3. Save
4. Verify pricing reflected in availability searches
**Expected**: Rate updates propagate

---

## Section D: Calendar & Bookings

### A-016: View Calendar (P0)
**Steps**:
1. Navigate to `/calendar`
2. Verify month grid renders
3. Select different property
4. Verify grid updates
5. Verify color coding for availability
**Expected**: Calendar loads with correct occupancy colors

### A-017: Block Dates (P1)
**Steps**:
1. On calendar, click a date cell
2. Open Block Date modal
3. Select reason
4. Save
5. Verify cell shows blocked state
6. Verify availability API returns 0 for those dates
**Expected**: Dates blocked, inventory reduced

### A-018: Create Manual Booking (P0)
**Steps**:
1. Navigate to `/bookings/manual`
2. Select property
3. Select room type
4. Pick dates
5. Fill guest details
6. Select source (walk-in)
7. Select payment method (cash)
8. Submit
9. Verify booking created
10. Verify booking appears in dashboard counts
**Expected**: Booking created, inventory held

### A-019: View Booking Detail (P0)
**Steps**:
1. Navigate to `/bookings/{id}`
2. Verify all details display: guest, dates, amounts, status
3. Verify invoice viewer loads
4. Verify payment status
**Expected**: Complete booking information visible

### A-020: Edit Booking (P0)
**Steps**:
1. Open booking detail
2. Click "Edit"
3. Extend checkout date
4. Save
5. Verify new amount calculated
6. Verify modification log entry created
**Expected**: Booking updated, audit trail maintained

### A-021: Cancel Booking with Refund (P0)
**Steps**:
1. Open confirmed booking
2. Click "Cancel"
3. Select cancellation reason
4. Verify refund amount calculated per policy
5. Confirm cancellation
6. Verify status changed to "cancelled"
7. Verify inventory released
**Expected**: Proper cancellation and refund

---

## Section E: Package Management

### A-022: Create Package (P1)
**Steps**:
1. Navigate to `/packages`
2. Click "Create Package"
3. Fill name, description
4. Add room composition
5. Add pricing rules (seasonal, weekend)
6. Add add-ons with slot times
7. Set active = true
8. Save
9. Verify package appears in list
**Expected**: Package created with all rules

### A-023: Package Appears in Search (P1)
**Steps**:
1. Create active package
2. Go to public site `/book`
3. Search for property dates
4. Verify package appears as option
5. Verify package price calculated correctly
**Expected**: Package visible to guests

---

## Section F: OTA Management

### A-024: Review OTA Queue (P1)
**Steps**:
1. Navigate to `/ota/queue`
2. Verify parsed booking cards load
3. Filter by source (Airbnb, MMT, Goibibo)
4. Verify counts match dashboard
**Expected**: Queue items load with confidence scores

### A-025: Confirm OTA Booking (P0)
**Steps**:
1. In queue, find pending booking
2. Click "Confirm"
3. Verify booking created in system
4. Verify inventory allocated
5. Verify email sent to guest
**Expected**: Booking imported successfully

### A-026: Reject OTA Booking (P1)
**Steps**:
1. Find low-confidence booking
2. Click "Reject"
3. Enter reason
4. Confirm
5. Verify booking status = rejected
**Expected**: Booking rejected with reason logged

### A-027: OTA Mappings CRUD (P0)
**Steps**:
1. Navigate to `/ota/mappings`
2. Click "Add Mapping"
3. Select property, room type, source, listing ID
4. Save
5. Verify mapping appears in table
6. Edit mapping, change listing ID
7. Save
8. Delete mapping
9. Verify soft-deleted
**Expected**: Full CRUD works

---

## Section G: Owner Reporting

### A-028: View Owner Dashboard (P1)
**Steps**:
1. Navigate to `/owner`
2. Select property
3. Select month
4. Click "Generate Report"
5. Verify P&L summary loads
6. Verify payout history loads
7. Verify monthly statement loads
**Expected**: All reports generate with data

### A-029: Owner Report Export (P2)
**Steps**:
1. Generate owner report
2. Click "Download PDF"
3. Verify PDF generates
**Expected**: PDF export available

---

## Section H: Admin Panel

### A-030: Feature Flags (P0)
**Steps**:
1. Navigate to `/admin`
2. Click "Feature Flags" tab
3. Toggle a feature on/off
4. Verify toggle persists after refresh
5. Verify feature visible/hidden in UI
**Expected**: Feature flags control UI elements

### A-031: System Settings (P0)
**Steps**:
1. Click "System Settings" tab
2. Update GST rate
3. Update currency
4. Save
5. Verify changes reflected in booking calculations
**Expected**: Settings propagate to pricing

### A-032: User Management (P0)
**Steps**:
1. Click "User Management" tab
2. View user list
3. Click "Invite User"
4. Fill email, select role (Manager)
5. Send invitation
6. Verify new user appears in list
7. Verify login works for new user
**Expected**: User invited and can login

### A-033: OTA Settings (P1)
**Steps**:
1. Click "OTA Settings" tab
2. Configure Gmail OAuth
3. Set polling interval
4. Save
5. Verify settings persisted
**Expected**: OTA integration configured

---

## Section I: Messages

### A-034: Compose Guest Message (P1)
**Steps**:
1. Navigate to `/messages`
2. Select a booking from list
3. Verify guest details auto-filled
4. Select "Welcome" template
5. Verify variables replaced in preview
6. Edit message
7. Click "Copy Text"
8. Click "Send via WhatsApp"
9. Verify WhatsApp Web opens with pre-filled message
**Expected**: Message composed and WhatsApp link works

---

## Section J: Public Site (As Admin)

### A-035: Public Site Works (P1)
**Steps**:
1. Open `/book` in incognito
2. Verify landing page loads with properties
3. Perform search
4. Verify results
**Expected**: Public site functional without login

---

## Section K: Edge Cases & Security

### A-036: SQL Injection Attempt (P0)
**Steps**:
1. In property name field, enter `' OR 1=1 --`
2. Save
3. Verify input sanitized
**Expected**: No SQL error, text stored literally

### A-037: XSS Attempt (P0)
**Steps**:
1. In property name, enter `<script>alert('xss')</script>`
2. Save
3. Verify script not executed
**Expected**: Text rendered as plain text

### A-038: Access Other User's Data (P0)
**Steps**:
1. Login as admin
2. Directly access `/bookings/{another-user-booking-id}`
3. Verify access granted (admin can see all)
**Expected**: Admin can access all data

### A-039: Invalid JWT Tampering (P0)
**Steps**:
1. Modify JWT in localStorage
2. Refresh page
3. Verify redirected to login
**Expected**: Invalid token rejected

### A-040: Role Escalation Attempt (P0)
**Steps**:
1. Login as Manager (create one first)
2. Try to access `/admin`
3. Verify access denied
4. Try to modify JWT role to "Admin"
5. Refresh
6. Verify still denied or redirected
**Expected**: Backend validates role, not just JWT claim

---

## Section L: Data Integrity

### A-041: Booking Cancellation Restores Inventory (P0)
**Steps**:
1. Check availability for date X = 5 rooms
2. Create booking for 2 rooms on date X
3. Verify availability = 3
4. Cancel booking
5. Verify availability = 5
**Expected**: Inventory properly restored

### A-042: Duplicate Booking Prevention (P0)
**Steps**:
1. Create booking with idempotency key
2. Submit same request again
3. Verify no duplicate created
**Expected**: Same booking returned, no duplicate

### A-043: Overbooking Prevention (P0)
**Steps**:
1. Property has 1 room
2. Book that room
3. Try to book same dates
4. Verify 409 conflict with alternatives
**Expected**: Overbooking blocked, alternatives suggested

---

## Admin Role Test Summary

| Section | Scenarios | Pass | Fail | Blocked |
|---------|-----------|------|------|---------|
| Auth & Setup | 7 | | | |
| Dashboard | 3 | | | |
| Properties | 5 | | | |
| Calendar & Bookings | 6 | | | |
| Packages | 2 | | | |
| OTA | 4 | | | |
| Owner Reporting | 2 | | | |
| Admin Panel | 4 | | | |
| Messages | 1 | | | |
| Public Site | 1 | | | |
| Security | 5 | | | |
| Data Integrity | 3 | | | |
| **Total** | **43** | | | |
