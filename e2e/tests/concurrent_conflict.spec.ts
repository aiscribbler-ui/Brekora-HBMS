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
    data: { name: 'E2E Concurrent Property', address: 'Test Address' },
  });
  expect(res.ok()).toBeTruthy();
  return res.json();
}

async function createRoomType(request: APIRequestContext, propertyId: string) {
  const res = await request.post(`${API_BASE}/properties/${propertyId}/room-types`, {
    headers: { 'X-Org-ID': DEFAULT_ORG_ID },
    data: {
      name: 'Solo Room',
      count: 1,
      base_capacity: 2,
      max_capacity: 3,
      default_rate: 2500.0,
    },
  });
  expect(res.ok()).toBeTruthy();
  return res.json();
}

async function getBookingsByProperty(request: APIRequestContext, propertyId: string) {
  const res = await request.get(`${API_BASE}/bookings/by-property/${propertyId}`, {
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

async function fillBookingFlow(page: Page, checkIn: string, checkOut: string, propertyId: string, roomTypeId: string) {
  await page.goto(
    `/book/flow?property_id=${propertyId}&item_id=${roomTypeId}&item_type=room&check_in=${checkIn}&check_out=${checkOut}&guests=2`
  );
  await page.fill('#guestName', 'Concurrent Guest');
  await page.fill('#guestEmail', 'concurrent@example.com');
  await page.fill('#guestPhone', '9876543210');
  await page.click('button:has-text("Next")');
  await expect(page.locator('text=Review Booking')).toBeVisible();
}

test('E2E-007: Concurrent Conflict', async ({ browser, request }) => {
  const checkIn = tomorrow(7);
  const checkOut = tomorrow(8);

  // 1. Create a property with exactly 1 room
  const property = await createProperty(request);
  const roomType = await createRoomType(request, property.id);

  // 2. Open two independent browser contexts
  const contextA = await browser.newContext();
  const contextB = await browser.newContext();
  const pageA = await contextA.newPage();
  const pageB = await contextB.newPage();

  // 3. Both guests navigate to the same booking flow and fill details
  await fillBookingFlow(pageA, checkIn, checkOut, property.id, roomType.id);
  await fillBookingFlow(pageB, checkIn, checkOut, property.id, roomType.id);

  // 4. Set up response watchers before clicking
  const responsePromiseA = pageA.waitForResponse(
    (resp) => resp.url().includes('/bookings/init')
  );
  const responsePromiseB = pageB.waitForResponse(
    (resp) => resp.url().includes('/bookings/init')
  );

  // 5. Click "Hold & Continue" on both pages simultaneously
  await Promise.all([
    pageA.click('button:has-text("Hold & Continue")'),
    pageB.click('button:has-text("Hold & Continue")'),
  ]);

  const [respA, respB] = await Promise.all([responsePromiseA, responsePromiseB]);
  const statusA = respA.status();
  const statusB = respB.status();

  // 6. One must succeed (201) and the other must conflict (409)
  const statuses = [statusA, statusB].sort();
  expect(statuses).toEqual([201, 409]);

  // 7. Verify UI states
  const successPage = statusA === 201 ? pageA : pageB;
  const conflictPage = statusA === 409 ? pageA : pageB;

  await expect(successPage.locator('text=Payment')).toBeVisible({ timeout: 10000 });
  await expect(conflictPage.locator('[role="alert"]')).toBeVisible({ timeout: 10000 });

  // 8. Verify via API: only 1 booking exists for this property
  const bookings = await getBookingsByProperty(request, property.id);
  expect(bookings.length).toBe(1);
  expect(bookings[0].status).toBe('pending_payment');

  // 9. Verify via API: availability is 0 because the single room is held
  const avail = await getAvailability(request, property.id, roomType.id, checkIn, checkOut);
  const minAvail = Math.min(...avail.map((n: any) => n.available_count));
  expect(minAvail).toBe(0);

  await contextA.close();
  await contextB.close();
});
