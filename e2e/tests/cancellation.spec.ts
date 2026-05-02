import { test, expect, type APIRequestContext } from '@playwright/test';

const API_BASE = 'http://localhost:8000/api/v1';
const DEFAULT_ORG_ID = '00000000-0000-0000-0000-000000000001';

function tomorrow(offsetDays = 1): string {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}

async function createProperty(request: APIRequestContext) {
  const res = await request.post(`${API_BASE}/properties`, {
    headers: { 'X-Org-ID': DEFAULT_ORG_ID },
    data: { name: 'E2E Cancellation Property', address: 'Test Address' },
  });
  expect(res.ok()).toBeTruthy();
  return res.json();
}

async function createRoomType(request: APIRequestContext, propertyId: string) {
  const res = await request.post(`${API_BASE}/properties/${propertyId}/room-types`, {
    headers: { 'X-Org-ID': DEFAULT_ORG_ID },
    data: {
      name: 'Cancellation Room',
      count: 1,
      base_capacity: 2,
      max_capacity: 3,
      default_rate: 2500.0,
    },
  });
  expect(res.ok()).toBeTruthy();
  return res.json();
}

async function getAvailability(
  request: APIRequestContext,
  propertyId: string,
  roomTypeId: string,
  checkIn: string,
  checkOut: string
) {
  const res = await request.get(`${API_BASE}/availability/rooms`, {
    headers: { 'X-Org-ID': DEFAULT_ORG_ID },
    params: {
      property_id: propertyId,
      room_type_id: roomTypeId,
      check_in: checkIn,
      check_out: checkOut,
    },
  });
  expect(res.ok()).toBeTruthy();
  return res.json();
}

test('E2E-005: Cancellation + Audit Test', async ({ page, request }) => {
  test.setTimeout(30_000);
  const checkIn = tomorrow(3);
  const checkOut = tomorrow(4);

  // 1. Setup: create property and room type via API
  const property = await createProperty(request);
  const roomType = await createRoomType(request, property.id);

  // 2. Create a booking via API init (pending_payment + active inventory hold)
  const initRes = await request.post(`${API_BASE}/bookings/init`, {
    headers: { 'X-Org-ID': DEFAULT_ORG_ID, 'Content-Type': 'application/json' },
    data: {
      property_id: property.id,
      item_type: 'room',
      item_id: roomType.id,
      check_in: checkIn,
      check_out: checkOut,
      guests: 2,
      channel_source: 'walk_in',
    },
  });
  expect(initRes.ok()).toBeTruthy();
  const initData = await initRes.json();
  const bookingId = initData.booking_id as string;
  expect(bookingId).toBeTruthy();

  // 3. Confirm the booking via API and attach a cancellation policy snapshot
  const policySnapshot = {
    is_non_refundable: false,
    free_cancellation_hours: 48,
    partial_refund_hours: 24,
    partial_refund_percentage: 50,
  };
  const patchRes = await request.patch(`${API_BASE}/bookings/${bookingId}`, {
    headers: { 'X-Org-ID': DEFAULT_ORG_ID, 'Content-Type': 'application/json' },
    data: {
      status: 'confirmed',
      cancellation_policy_snapshot: policySnapshot,
    },
  });
  expect(patchRes.ok()).toBeTruthy();
  const confirmedBooking = await patchRes.json();
  expect(confirmedBooking.status).toBe('confirmed');

  // 4. Verify room is unavailable before cancellation
  const availBefore = await getAvailability(request, property.id, roomType.id, checkIn, checkOut);
  const minAvailBefore = Math.min(...availBefore.map((n: any) => n.available_count));
  expect(minAvailBefore).toBe(0);

  // 5. Manager logs in via frontend
  await page.goto('/login');
  await page.fill('#email', 'e2e-manager@brekora.test');
  await page.fill('#password', 'E2EManager123!');
  await page.click('button[type="submit"]:has-text("Sign In")');
  await page.waitForURL('/dashboard');

  // 6. Navigate to booking detail page
  await page.goto(`/bookings/${bookingId}`);
  await expect(page.locator('text=Booking Details')).toBeVisible({ timeout: 10_000 });

  // 7. Click Cancel button and open modal
  await page.click('button:has-text("Cancel Booking")');
  await expect(page.locator('text=Cancel Booking').first()).toBeVisible({ timeout: 10_000 });

  // 8. Verify refund calculator shows expected refund (3 days = 72h >= 48h free cancellation => full refund)
  const expectedRefund = confirmedBooking.total_amount as number;
  await expect(page.locator('span.text-green-700.font-bold')).toHaveText(`₹${expectedRefund.toFixed(2)}`);

  // 9. Enter cancellation reason and confirm
  const cancellationReason = 'Guest changed plans';
  await page.fill('#cancellationReason', cancellationReason);
  await page.click('button:has-text("Confirm Cancellation")');

  // 10. Wait for success toast and frontend status update
  await expect(page.locator('text=Booking cancelled successfully.')).toBeVisible({ timeout: 10_000 });
  await expect(page.locator('span.capitalize:has-text("cancelled")')).toBeVisible({ timeout: 10_000 });

  // 11. API verification: booking is cancelled with correct fields
  const bookingRes = await request.get(`${API_BASE}/bookings/${bookingId}`, {
    headers: { 'X-Org-ID': DEFAULT_ORG_ID },
  });
  expect(bookingRes.ok()).toBeTruthy();
  const booking = await bookingRes.json();
  expect(booking.status).toBe('cancelled');
  expect(booking.cancelled_at).toBeTruthy();
  expect(booking.cancellation_reason).toBe(cancellationReason);

  // 12. Verify modification_log contains cancellation audit entry
  expect(Array.isArray(booking.modification_log)).toBe(true);
  expect(booking.modification_log.length).toBeGreaterThan(0);
  const lastLog = booking.modification_log[booking.modification_log.length - 1];
  expect(lastLog.reason).toContain(cancellationReason);
  expect(lastLog.changes.status.old).toBe('confirmed');
  expect(lastLog.changes.status.new).toBe('cancelled');

  // 13. Verify availability is restored after cancellation
  const availAfter = await getAvailability(request, property.id, roomType.id, checkIn, checkOut);
  const minAvailAfter = Math.min(...availAfter.map((n: any) => n.available_count));
  expect(minAvailAfter).toBe(1);
});
