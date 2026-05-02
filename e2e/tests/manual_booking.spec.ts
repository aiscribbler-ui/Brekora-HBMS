import { test, expect } from '@playwright/test';

function tomorrow(offsetDays = 1) {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return d.toISOString().split('T')[0];
}

test('E2E-002: Manual Booking Flow', async ({ page, request }) => {
  test.setTimeout(30_000);

  // Manager login
  await page.goto('/login');
  await page.fill('#email', 'e2e-manager@brekora.test');
  await page.fill('#password', 'E2EManager123!');
  await page.click('button[type="submit"]:has-text("Sign In")');
  await page.waitForURL('/dashboard');

  // Navigate to manual booking form
  await page.goto('/bookings/manual');

  // Step 1: booking details
  await page.selectOption('#propertyId', { label: 'E2E Test Property' });
  await page.locator('input[value="room"]').check();
  await page.selectOption('#itemId', { label: /Standard Room/ });
  await page.fill('#checkIn', tomorrow(3));
  await page.fill('#checkOut', tomorrow(4));
  await page.fill('#guests', '2');
  await page.click('button:has-text("Next")');

  // Step 2: guest details
  await page.fill('#guestName', 'Walk-in Guest');
  await page.fill('#guestEmail', 'walkin@example.com');
  await page.fill('#guestPhone', '9123456789');
  await page.fill('#guestIdNumber', 'ABC123456');
  await page.click('button:has-text("Next")');

  // Step 3: source & payment
  await page.locator('input[value="walk_in"]').check();
  await page.locator('input[value="cash"]').check();
  await page.click('button:has-text("Next")');

  // Step 4: confirm and capture booking id
  const [initResponse] = await Promise.all([
    page.waitForResponse(
      (resp) => resp.url().includes('/api/v1/bookings/init') && resp.status() === 201
    ),
    page.click('button:has-text("Confirm & Record Payment")'),
  ]);
  const initData = await initResponse.json();
  const bookingId = initData.booking_id as string;
  expect(bookingId).toBeTruthy();

  // Verify backend booking
  const bookingResp = await request.get(`/api/v1/bookings/${bookingId}`, {
    headers: { 'X-Org-ID': '00000000-0000-0000-0000-000000000001' },
  });
  expect(bookingResp.status()).toBe(200);
  const booking = await bookingResp.json();
  expect(booking.source_type).toBe('walk_in');
});
