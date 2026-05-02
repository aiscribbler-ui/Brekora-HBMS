import { test, expect, type Page, type APIRequestContext } from '@playwright/test';

const API_BASE = 'http://localhost:8000/api/v1';
const DEFAULT_ORG_ID = '00000000-0000-0000-0000-000000000001';

function tomorrow(offsetDays = 7): string {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}

async function createProperty(request: APIRequestContext) {
  const res = await request.post(`${API_BASE}/properties`, {
    headers: { 'X-Org-ID': DEFAULT_ORG_ID },
    data: { name: 'E2E Payment Recovery Property', address: 'Test Address' },
  });
  expect(res.ok()).toBeTruthy();
  return res.json();
}

async function createRoomType(request: APIRequestContext, propertyId: string) {
  const res = await request.post(`${API_BASE}/properties/${propertyId}/room-types`, {
    headers: { 'X-Org-ID': DEFAULT_ORG_ID },
    data: {
      name: 'Deluxe Room',
      count: 1,
      base_capacity: 2,
      max_capacity: 3,
      default_rate: 2500.0,
    },
  });
  expect(res.ok()).toBeTruthy();
  return res.json();
}

async function getBooking(request: APIRequestContext, bookingId: string) {
  const res = await request.get(`${API_BASE}/bookings/${bookingId}`, {
    headers: { 'X-Org-ID': DEFAULT_ORG_ID },
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

async function createOrder(request: APIRequestContext, bookingId: string) {
  const res = await request.post(`${API_BASE}/payments/create-order`, {
    headers: { 'X-Org-ID': DEFAULT_ORG_ID, 'Content-Type': 'application/json' },
    data: { booking_id: bookingId },
  });
  expect(res.ok()).toBeTruthy();
  return res.json();
}

async function simulateWebhook(request: APIRequestContext, event: string, orderId: string, errorDescription?: string) {
  const payload: Record<string, unknown> = {
    event,
    id: `evt_${event.replace('.', '_')}_${Date.now()}`,
    payload: {
      payment: {
        entity: {
          id: `pay_${Date.now()}`,
          order_id: orderId,
          ...(errorDescription ? { error_description: errorDescription } : {}),
        },
      },
    },
  };
  const res = await request.post(`${API_BASE}/webhooks/razorpay`, {
    headers: { 'Content-Type': 'application/json', 'X-Razorpay-Signature': 'mock-sig' },
    data: payload,
  });
  expect(res.ok()).toBeTruthy();
}

async function fillBookingFlow(page: Page, checkIn: string, checkOut: string, propertyId: string, roomTypeId: string) {
  await page.goto(
    `/book/flow?property_id=${propertyId}&item_id=${roomTypeId}&item_type=room&check_in=${checkIn}&check_out=${checkOut}&guests=2`
  );
  await page.fill('#guestName', 'Test Guest');
  await page.fill('#guestEmail', 'test@example.com');
  await page.fill('#guestPhone', '9876543210');
  await page.click('button:has-text("Next")');
  await expect(page.locator('text=Review Booking')).toBeVisible();
}

test('E2E-006: Payment Failure Recovery', async ({ page, request }) => {
  const checkIn = tomorrow(7);
  const checkOut = tomorrow(8);

  // 1. Setup test data
  const property = await createProperty(request);
  const roomType = await createRoomType(request, property.id);

  // 2. Guest initiates booking via frontend
  await fillBookingFlow(page, checkIn, checkOut, property.id, roomType.id);

  const initResponsePromise = page.waitForResponse(
    (resp) => resp.url().includes('/bookings/init') && resp.status() === 201
  );
  await page.click('button:has-text("Hold & Continue")');
  const initResponse = await initResponsePromise;
  const initData = await initResponse.json();
  const bookingId = initData.booking_id as string;

  await expect(page.locator('text=Payment')).toBeVisible({ timeout: 10000 });

  // 3. Create Razorpay order
  const orderData = await createOrder(request, bookingId);
  const orderId = orderData.order_id as string;

  // 4. Verify inventory is held (availability drops to 0)
  const availBeforeFail = await getAvailability(request, property.id, roomType.id, checkIn, checkOut);
  const minAvailBeforeFail = Math.min(...availBeforeFail.map((n: any) => n.available_count));
  expect(minAvailBeforeFail).toBe(0);

  // 5. Simulate payment failure via webhook
  await simulateWebhook(request, 'payment.failed', orderId, 'Card declined by bank');

  // 6. Verify booking status is payment_failed
  const bookingAfterFail = await getBooking(request, bookingId);
  expect(bookingAfterFail.status).toBe('payment_failed');

  // 7. Verify inventory was released on failure
  const availAfterFail = await getAvailability(request, property.id, roomType.id, checkIn, checkOut);
  const minAvailAfterFail = Math.min(...availAfterFail.map((n: any) => n.available_count));
  expect(minAvailAfterFail).toBe(1);

  // 8. Guest retries payment via API (frontend retry UI is stubbed)
  const retryRes = await request.post(`${API_BASE}/bookings/${bookingId}/retry-payment`, {
    headers: { 'X-Org-ID': DEFAULT_ORG_ID },
  });
  expect(retryRes.ok()).toBeTruthy();
  const retryData = await retryRes.json();
  expect(retryData.hold_id).toBeTruthy();

  // 9. Verify inventory re-held on retry
  const availAfterRetry = await getAvailability(request, property.id, roomType.id, checkIn, checkOut);
  const minAvailAfterRetry = Math.min(...availAfterRetry.map((n: any) => n.available_count));
  expect(minAvailAfterRetry).toBe(0);

  // 10. Verify booking returned to pending_payment
  const bookingAfterRetry = await getBooking(request, bookingId);
  expect(bookingAfterRetry.status).toBe('pending_payment');

  // 11. Create a fresh order for the retry and simulate success
  const retryOrderData = await createOrder(request, bookingId);
  const retryOrderId = retryOrderData.order_id as string;
  await simulateWebhook(request, 'payment.captured', retryOrderId);

  // 12. Verify booking confirmed after success
  const bookingAfterSuccess = await getBooking(request, bookingId);
  expect(bookingAfterSuccess.status).toBe('confirmed');

  // 13. Verify inventory stays committed (availability still 0 because booking is confirmed)
  const availAfterSuccess = await getAvailability(request, property.id, roomType.id, checkIn, checkOut);
  const minAvailAfterSuccess = Math.min(...availAfterSuccess.map((n: any) => n.available_count));
  expect(minAvailAfterSuccess).toBe(0);
});
