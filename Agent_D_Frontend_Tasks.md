# Agent D — Frontend Tasks

## FE-006: Manual Booking Creation Form

### Acceptance Criteria
- [x] Multi-step form (property, item, dates, guests → guest details → source & payment → review)
- [x] React Hook Form + Zod validation
- [x] Live availability warning with insufficient inventory detection
- [x] 409 conflict handling with alternative suggestions
- [x] Add-on selection support for packages
- [x] Payment method selector (cash, UPI, card, bank_transfer, pay_later)
- [x] Price breakdown shown on review step
- [x] `initBooking` called on review/confirm to hold inventory
- [x] Route `/bookings/manual` protected by manager auth
- [x] Uses existing axios instance and UI patterns

## FE-012: Direct Booking Site (Public)

### Acceptance Criteria
- [x] Public landing page at `/book` with property showcase and search bar
- [x] Search results page at `/book/search` displaying rooms and packages
- [x] Sold-out items visually greyed out
- [x] Package badges on package cards
- [x] Multi-step booking flow at `/book/flow` (details → review → payment)
- [x] `initBooking` called on review step to hold inventory
- [x] `createOrder` called to get Razorpay order ID
- [x] Razorpay JS SDK loaded dynamically via CDN
- [x] Payment success redirects to confirmation page
- [x] Payment failure/conflict shows "Just booked" banner with retry option
- [x] Confirmation page at `/book/confirm` with booking reference
- [x] Mobile responsive (Tailwind responsive classes)
- [x] Public routes — no auth required
