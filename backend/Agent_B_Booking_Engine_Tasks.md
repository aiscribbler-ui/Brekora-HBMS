# Agent B Booking Engine Tasks

## B-008: Payment Confirmation

### Acceptance Criteria
- [x] `_handle_payment_captured` logs an info stub with booking ID and guest email
- [x] `test_payment_captured_confirms_booking` verifies booking confirmed, payment captured, inventory committed
- [x] `test_duplicate_webhook_idempotent` verifies idempotency via FakeRedis (no double-commit)
- [x] `test_payment_captured_without_hold` verifies booking still confirmed when hold missing/expired

## B-009: Payment Failure Handling

### Acceptance Criteria
- [x] `FailedPayment` model created with fields: id, org_id, booking_id, reason, attempt_number, created_at, updated_at
- [x] Alembic migration `0022_add_failed_payment.py` created and applied
- [x] `_handle_payment_failed` creates `FailedPayment` record with reason and incremented attempt_number
- [x] `check_payment_timeouts` detects pending bookings >10 min old without captured payment, releases inventory, marks booking `payment_failed`, creates `FailedPayment` with reason="timeout"
- [x] `test_payment_failed_releases_inventory` verifies inventory released, booking marked failed, FailedPayment created
- [x] `test_payment_timeout_detected` verifies old pending booking is timed out
- [x] `test_failed_payment_increment_attempt` verifies attempt_number increments across multiple failures

## B-010: Guest Retry Payment Flow (BKG-006)

### Acceptance Criteria
- [x] `BookingInitService.retry_payment` validates booking exists and status is `payment_failed`
- [x] Reuses active hold if still within 10 min TTL
- [x] Re-checks availability and creates new hold if old hold expired/released
- [x] Calls `PaymentService.create_order` to generate fresh Razorpay order
- [x] Tracks retry count in Redis (`retry:{booking_id}`)
- [x] Enforces max 3 retry attempts per booking
- [x] `POST /bookings/{booking_id}/retry-payment` endpoint returns `BookingInitResponse`
- [x] Appropriate `HTTPException` raised for `ValueError` (400/409)
- [x] Tests cover: re-hold, reuse active hold, 409 on no inventory, max retries, confirmed rejection

## BKG-012: Add-on Slot Selection Backend

### Acceptance Criteria
- [x] `init_booking` validates slot add-ons before creating booking record
- [x] `BookingConflictError` raised with slot alternatives when slot unavailable
- [x] Alternatives include `item_type="add_on_slot"`, `item_name`, `available_count`, `suggested_price`, `currency`
- [x] `AddOnSlotService.get_available_slots` queries `AddOnCapacity` for available slots
- [x] Tests cover: valid slot success, unavailable slot conflict, alternatives format
