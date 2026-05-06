# Brekora HBMS — Comprehensive Frontend Requirements Mapping

## 1. Role Definitions & Access Matrix

| Role | Code | Description | Sidebar Access |
|------|------|-------------|--------------|
| **Admin** | `Admin` | Full system access. Manages users, feature flags, OTA settings, system config. | Dashboard, Properties, Calendar, Packages, OTA Queue, New Booking, Owner, Admin |
| **Property Manager** | `Manager` | Day-to-day operations. Manages bookings, calendar, OTA queue, packages for assigned properties. | Dashboard, Properties, Calendar, Packages, OTA Queue, New Booking |
| **Owner** | `Owner` | Views P&L reports, payout history, monthly statements. Read-only on most operational data. | Dashboard, Properties (view), Calendar (view), Owner |
| **Partner** | `Partner` | External agent who lists properties on behalf of owners. Needs a subset of manager tools + commission view. | **Not yet implemented** |
| **Guest / Direct Booking User** | `Guest` | Public-facing user who searches, books, pays. No backend access. | Guest Dashboard (separate route) |
| **All Listing Manager** | `ListingManager` | Cross-property role that manages OTA listings, content, photos across multiple properties. | **Not yet implemented** |

**Clarification needed:** You listed 5 roles but said "4 type of logins". The PRD codebase currently recognizes `Admin`, `Manager`, `Owner`, and `Guest`. `Partner` and `ListingManager` are referenced in your ask but do not yet exist in the backend role model or JWT claims. See Open Questions at the end.

---

## 2. Page-by-Page Inventory

### A. Authentication & Onboarding

#### A-1. `/login` — Staff Login
**Elements:**
- Email input
- Password input
- Submit button
- "Forgot password?" link (currently disabled/stub)
- Error banner (rate limit, invalid credentials)

**Functionality:**
- POST `/auth/login`
- If `requires_2fa: true`, redirect to `/2fa`
- Otherwise store tokens in Zustand + localStorage, decode JWT for role/name, redirect `/dashboard`
- Auto-refresh token 60s before expiry

**Roles:** All staff roles (Admin, Manager, Owner, Partner, ListingManager)

---

#### A-2. `/2fa` — Two-Factor Verification
**Elements:**
- TOTP code input (6 digits)
- Submit button
- "Use backup code" option (if implemented)

**Functionality:**
- POST `/auth/2fa/verify`
- On success: same flow as login

**Roles:** All staff roles when 2FA is enabled

---

#### A-3. `/guest/login` — Guest Login
**Elements:**
- Email input
- Password input
- Submit button
- "Don't have an account? Sign up" link

**Functionality:**
- Separate guest auth service (`guestApi.ts`)
- Stores guest tokens separately

**Roles:** Guest only

---

#### A-4. `/guest/signup` — Guest Registration
**Elements:**
- Name input
- Email input
- Phone input
- Password input
- Submit button

**Functionality:**
- POST `/users/guest` (or equivalent guest registration endpoint)
- Auto-login after signup

**Roles:** Guest only

---

#### A-5. **First-Time Admin Setup** — **MISSING PAGE**
**Current gap:** There is no "seed admin" or "first organization setup" flow. When the backend starts with an empty DB, no user exists and the login page has no way to create the first admin.

**Proposed page:** `/setup` or `/admin/setup`
**Elements:**
- Organization name input
- Admin full name input
- Admin email input
- Admin password input (with strength meter)
- Confirm password
- Submit button

**Functionality:**
- POST `/auth/setup` (new backend endpoint needed)
- Should only work when `User` table is empty (secure, one-time use)
- Creates default org + Admin role + first user
- Redirects to `/login` after success

**Roles:** No auth required (one-time setup)

---

### B. Dashboard

#### B-1. `/dashboard` — Manager Dashboard
**Elements:**
- Page header: "Manager Dashboard" + subtitle
- Refresh button (manual)
- Today View card: Arrivals, Departures, In-House, Pending Check-ins
- Week Summary card: Occupancy % progress bar, ADR by property list
- Open Tasks card: OTA Queue Review count, Payment Failures count, Pending Refunds count
- Quick Actions card: Create Booking, Block Dates, Message Guest, Review OTA Queue, Edit OTA Mapping
- Properties List card: Property name, address, active/inactive badge

**Functionality:**
- Auto-refresh every 60 seconds
- Real data from:
  - `/properties`
  - `/bookings` (filtered by check_in/check_out = today)
  - `/availability/rooms`
  - `/ota/alerts/count`

**Roles:** Admin, Manager, Owner (read-only view for Owner)

---

### C. Properties

#### C-1. `/properties` — Property List
**Elements:**
- Page header + "Add Property" button
- Table/grid of properties: Name, Address, Status, Actions
- Search/filter bar

**Functionality:**
- GET `/properties`
- Click row → `/properties/:id`
- "Add Property" → navigate to form

**Roles:** Admin, Manager, ListingManager

---

#### C-2. `/properties/:id` — Property Detail
**Elements:**
- Property name, address, status badge
- Photo gallery
- Amenities list
- Room Types section with "Add Room Type" button
- OTA Mappings section (if configured)
- Edit / Delete buttons

**Functionality:**
- GET `/properties/:id`
- DELETE property
- Navigate to room types

**Roles:** Admin, Manager, ListingManager (read-only for Owner)

---

#### C-3. `/properties/:id/room-types` — Room Type List
**Elements:**
- Room type cards: Name, count, base rate, occupancy
- "Add Room Type" button
- Edit / Delete per row

**Functionality:**
- GET `/properties/:id/room-types`

**Roles:** Admin, Manager, ListingManager

---

#### C-4. `/properties/:id/room-types/:roomTypeId` — Room Type Form
**Elements:**
- Name input
- Count input
- Base rate input
- Min stay / Max stay inputs
- Photo uploader
- Amenities multi-select
- Submit / Cancel buttons

**Functionality:**
- GET (edit mode) or POST (create mode) `/room-types`
- Form validation via Zod + React Hook Form

**Roles:** Admin, Manager, ListingManager

---

### D. Calendar

#### D-1. `/calendar` — Calendar Grid
**Elements:**
- Month view grid
- Property selector dropdown
- Room type filter
- Date cells with availability color coding
- Block Date modal trigger

**Functionality:**
- GET `/availability/rooms` for date range
- Click cell → open Block Date modal
- POST to create inventory holds / block dates

**Roles:** Admin, Manager, Owner (view only)

---

### E. Packages

#### E-1. `/packages` — Package List
**Elements:**
- Package cards: Name, description, price, active status
- "Create Package" button
- Edit / Delete actions

**Functionality:**
- GET `/packages`
- Navigate to builder

**Roles:** Admin, Manager

---

#### E-2. `/packages/:id` — Package Builder
**Elements:**
- Package name, description inputs
- Room composition builder (room type + count)
- Pricing rules section (seasonal rates, weekend rates)
- Add-on selector with slot times
- Active toggle
- Submit / Cancel

**Functionality:**
- GET/PUT/POST `/packages`
- Complex nested form with Zod validation

**Roles:** Admin, Manager

---

### F. Bookings (Backend / Manual)

#### F-1. `/bookings/manual` — Manual Booking Form
**Elements:**
- Step indicator (BookingSteps component)
- Property selector
- Item type toggle (Room / Package)
- Item selector
- Check-in / Check-out date pickers
- Guest count
- Guest details form (name, email, phone, ID)
- Source selector (walk-in, phone, whatsapp, referral)
- Payment method selector
- Promo code input
- Add-on slot selection
- Conflict banner (if room unavailable with alternatives)
- Submit button

**Functionality:**
- POST `/bookings/init` then `/orders` then `/payments/capture`
- Real-time availability check
- Conflict resolution with alternative suggestions

**Roles:** Admin, Manager

---

#### F-2. `/bookings/:id` — Booking Detail
**Elements:**
- Booking reference, status badge
- Guest details card
- Room/package details
- Stay dates, guest count
- Payment status
- Add-ons list
- Invoice viewer
- Refund calculator (if cancelled)
- Action buttons: Edit, Cancel, Send Invoice

**Functionality:**
- GET `/bookings/:id`
- Cancel with refund calculation
- View invoice PDF

**Roles:** Admin, Manager, Owner (view only), Guest (own bookings only)

---

#### F-3. `/bookings/:id/edit` — Booking Edit
**Elements:**
- Same as detail but editable
- Date extension / modification fields
- Guest detail edits
- Status changes (check-in, check-out, no-show)

**Functionality:**
- PUT `/bookings/:id`
- Cancellation policy enforcement
- Audit trail logging

**Roles:** Admin, Manager

---

### G. OTA Management

#### G-1. `/ota/queue` — OTA Email Queue
**Elements:**
- Filter tabs: All, Airbnb, MMT, Goibibo
- Parsed booking cards: Source, Guest name, Dates, Property, Room type, Amount
- Confidence score badge
- Action buttons: Confirm, Edit & Confirm, Reject
- Bulk select checkbox
- Refresh button

**Functionality:**
- GET `/ota/queue`
- POST `/ota/queue/:id/confirm`
- POST `/ota/queue/:id/reject`
- Edit modal for low-confidence bookings

**Roles:** Admin, Manager

---

#### G-2. **OTA Mappings** — `/ota/mappings` — **MISSING ROUTE**
**Current gap:** QuickActions has "Edit OTA Mapping" button but it redirects to `/properties`. There is no dedicated OTA mapping page.

**Proposed page:** `/ota/mappings`
**Elements:**
- Table: Property, OTA Source, External Property ID, External Room Type ID, Mapping status
- "Add Mapping" button
- Sync status / last sync time
- Bulk import from CSV

**Functionality:**
- GET/POST `/ota/mappings`
- Connection test per OTA source

**Roles:** Admin, Manager, ListingManager

---

### H. Owner Reporting

#### H-1. `/owner` — Owner Dashboard
**Elements:**
- Property selector dropdown
- Month picker
- "Generate Report" button
- P&L Summary card: Revenue, Expenses, Net, Tax, Commission
- Payout History card: Total bookings, Commission, Net payout, Status
- Monthly Statement table: Date, Description, Amount, Running balance

**Functionality:**
- GET `/owner/pnl`, `/owner/payout`, `/owner/statement`
- Filtered by property + month

**Roles:** Owner, Admin

---

### I. Admin Panel

#### I-1. `/admin` — Admin Panel
**Tabs:**
1. **Feature Flags** — Toggle system features on/off
2. **System Settings** — GST config, currency, default policies
3. **User Management** — List users, invite new users, assign roles, reset passwords
4. **OTA Settings** — Gmail OAuth, polling interval, parser settings

**Elements:**
- Tab sidebar
- Form components per tab
- Save / Reset buttons

**Functionality:**
- GET/PUT `/feature-flags`
- GET/PUT system config
- GET/POST `/users`
- GET/PUT `/ota/settings`

**Roles:** Admin only

---

### J. Public / Direct Booking Site

#### J-1. `/book` — Landing Page
**Elements:**
- Sticky header with Brekora logo + Guest Login link
- Gradient hero with animated blobs
- Search bar (location, check-in, check-out, guests) in floating white card
- Trust badges: Secure Payments, Curated Stays, Prime Locations, Modern Amenities
- Featured Properties grid: Photo, name, address, amenities chips, active badge
- Footer with branding

**Functionality:**
- GET `/properties` (public, filtered `is_active=true`)
- Search → navigate to `/book/search`

**Roles:** Public (no auth)

---

#### J-2. `/book/search` — Search Results
**Elements:**
- Search bar (sticky top, pre-filled)
- Results count
- Room cards: Photo, name, price/night, guests, amenities, "Book Now" button
- Package cards (if applicable)
- Loading skeleton
- Empty state

**Functionality:**
- GET `/search/availability`
- Filter by location, dates, guests
- Click "Book Now" → `/book/flow`

**Roles:** Public (no auth)

---

#### J-3. `/book/flow` — Booking Flow
**Elements:**
- Pre-filled booking summary (from search params)
- Guest details form: Name, email, phone, promo code
- Razorpay checkout button
- Conflict banner (if sold out during flow)
- Terms & conditions checkbox

**Functionality:**
- POST `/bookings/init` → `/orders` → Razorpay checkout
- Payment capture via webhook + frontend callback
- On success → `/book/confirm?booking_id=...`

**Roles:** Public (no auth required until payment)

---

#### J-4. `/book/confirm` — Booking Confirmation
**Elements:**
- Success animation / checkmark
- Booking reference number
- Property details
- Stay dates
- Guest details
- Download invoice button
- "Manage booking" link (requires guest login)

**Functionality:**
- GET `/bookings/:id` (from query param)

**Roles:** Public (or Guest if logged in)

---

### K. Guest Portal

#### K-1. `/guest` — Guest Dashboard
**Elements:**
- Welcome header with guest name
- My Bookings card (upcoming + past)
- Profile card (edit details)
- Logout button

**Functionality:**
- GET guest bookings
- View / modify own bookings
- Retry failed payments

**Roles:** Guest only

---

## 3. Missing Pages & Functionality Gaps

| # | Gap | Impact | Proposed Solution |
|---|-----|--------|-------------------|
| 1 | **First-time admin setup** | Blocker — fresh install has no way to create the first user | Add `/setup` page + `/auth/setup` backend endpoint |
| 2 | **Partner role & dashboard** | User explicitly asked for Partner login | Add `Partner` role to backend; create `/partner` dashboard with commission view |
| 3 | **Listing Manager role** | User explicitly asked for "all listing manager" | Add `ListingManager` role; create cross-property content management page |
| 4 | **OTA Mappings page** | QuickActions button redirects to wrong place | Build `/ota/mappings` page with mapping CRUD |
| 5 | **Forgot / Reset Password** | No password recovery flow | Add `/forgot-password` and `/reset-password` pages |
| 6 | **User Profile / Account Settings** | No way for staff to update their own profile | Add `/account` or `/settings/profile` page |
| 7 | **Booking List / Grid view** | No centralized bookings list; only dashboard counts | Add `/bookings` page with date filter, status filter, search |
| 8 | **Guest booking history API** | GuestDashboard says "You have no upcoming bookings" but has no API call | Wire `guestApi.ts` to fetch guest bookings |
| 9 | **Message Guest functionality** | QuickActions "Message Guest" navigates to booking form (wrong) | Either build in-app messaging or remove button |
| 10 | **Property photos on Landing** | Landing page shows `property.photos[0].url` but backend may not serve public photo URLs | Verify photo upload → public URL pipeline |
| 11 | **Admin user invitation** | AdminPanel UserManagement has no "Invite User" form | Add invite flow with email + role assignment |
| 12 | **Reports export (PDF/CSV)** | Owner reports are web-only | Add download buttons for PDF/CSV generation |

---

## 4. First-Time Admin Setup Flow (Recommended)

When the backend database is empty (no users, no org):

1. **Detection:** Frontend tries to GET `/auth/setup-status` (new endpoint)
   - If `setup_required: true`, redirect `/` → `/setup`
   - If `setup_required: false`, show normal `/login`

2. **Setup Page (`/setup`):**
   - Organization Name
   - Admin Email
   - Admin Password (strength validated)
   - Confirm Password
   - Submit → POST `/auth/setup`
   - Success → redirect to `/login` with flash message "Setup complete. Please log in."

3. **Backend security:**
   - `/auth/setup` returns 403 if any user already exists
   - Rate-limited to prevent brute-force probing

---

## 5. Open Questions

### Q1. Role Clarification
You listed 5 roles but said "4 type of logins". The codebase currently has:
- `Admin`, `Manager`, `Owner` (staff login at `/login`)
- `Guest` (public login at `/guest/login`)

**What exactly is the 5th role?**
- Is **Partner** the same as **Listing Manager**?
- Or are these two distinct roles (Partner = commission-based agent, Listing Manager = cross-property content admin)?
- What should each role be able to do that `Manager` cannot?

### Q2. Admin Setup Preference
Do you want:
- **A)** A web-based first-time setup page (as proposed above)?
- **B)** A CLI command (`python -m backend.scripts.create_admin`) that you run once in Docker?

### Q3. OTA Mapping Scope
For the "Edit OTA Mapping" button:
- **A)** Build a dedicated `/ota/mappings` page with CRUD?
- **B)** Keep redirecting to `/properties` and add mapping UI inside Property Detail?
- **C)** Remove the button for now?

### Q4. "Message Guest" Button
The QuickActions "Message Guest" currently goes to `/bookings/manual` (wrong). Should we:
- **A)** Build a simple guest messaging page (requires backend SMS/email API integration)?
- **B)** Open WhatsApp Web with pre-filled message?
- **C)** Remove the button?

### Q5. Partner / Listing Manager Urgency
Do you need these two new roles built now, or can they be Phase 2 after the core 3 staff roles are fully polished?

### Q6. Public Photo URLs
The Landing page expects `property.photos[0].url`. Does your backend currently:
- **A)** Store photos in S3 / public CDN with public URLs?
- **B)** Serve photos via authenticated endpoint (requires signed URLs)?
- **C)** Not yet handle photos at all?

This affects whether the Landing page can display real property images.

---

## 6. Existing Files Summary

| Category | Count | Key Files |
|----------|-------|-----------|
| Pages | 25 | `src/pages/*` |
| Components | 33 | `src/components/*` |
| Services | 11 | `src/services/*` |
| Hooks | 4 | `useAuth`, `useGuestAuth`, `useDashboard`, `useCalendar` |
| Tests | 71+ | Vitest + React Testing Library |
| Store | 1 | Zustand auth store with localStorage persistence |

All core routing, auth, and data fetching infrastructure is in place. The primary work ahead is:
1. Filling the 12 gaps listed in Section 3
2. Clarifying the 6 open questions above
3. Adding the 2 new roles (Partner + ListingManager) if confirmed
