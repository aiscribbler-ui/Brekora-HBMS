import { test, expect } from '@playwright/test';

function tomorrow(offsetDays = 1) {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return d.toISOString().split('T')[0];
}

test('E2E-001: Direct Booking Flow', async ({ page, request }) => {
  test.setTimeout(30_000);

  // Navigate to landing page
  await page.goto('/book');

  // Search for availability
  await page.fill('#location', 'Test City');
  await page.fill('#checkIn', tomorrow(1));
  await page.fill('#checkOut', tomorrow(2));
  await page.fill('#guests', '2');
  await page.click('button[type="submit"]:has-text("Search")');

  // Wait for results and select first room
  await page.waitForURL('/book/search?**');
  const selectBtn = page.locator('button:has-text("Select")').first();
  await expect(selectBtn).toBeVisible({ timeout: 10_000 });
  await selectBtn.click();

  // Fill guest details on booking flow
  await page.waitForURL('/book/flow?**');
  await page.fill('#guestName', 'E2E Guest');
  await page.fill('#guestEmail', 'e2e-guest@brekora.test');
  await page.fill('#guestPhone', '9876543210');
  await page.click('button:has-text("Next")');

  // Review step: hold inventory and capture booking id
  const [initResponse] = await Promise.all([
    page.waitForResponse(
      (resp) => resp.url().includes('/api/v1/bookings/init') && resp.status() === 201
    ),
    page.click('button:has-text("Hold & Continue")'),
  ]);
  const initData = await initResponse.json();
  const bookingId = initData.booking_id as string;
  expect(bookingId).toBeTruthy();

  // Payment step appears (stop before Razorpay)
  await expect(page.locator('text=Amount to pay')).toBeVisible({ timeout: 10_000 });

  // Verify backend booking status
  const bookingResp = await request.get(`/api/v1/bookings/${bookingId}`, {
    headers: { 'X-Org-ID': '00000000-0000-0000-0000-000000000001' },
  });
  expect(bookingResp.status()).toBe(200);
  const booking = await bookingResp.json();
  expect(booking.status).toBe('pending_payment');
});
