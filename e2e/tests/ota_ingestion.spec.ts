import { test, expect } from '@playwright/test';

test('E2E-003: OTA Parse + Confirm', async ({ page, request }) => {
  test.setTimeout(30_000);

  // Manager login
  await page.goto('/login');
  await page.fill('#email', 'e2e-manager@brekora.test');
  await page.fill('#password', 'E2EManager123!');
  await page.click('button[type="submit"]:has-text("Sign In")');
  await page.waitForURL('/dashboard');

  // Navigate to OTA queue
  await page.goto('/ota/queue');

  // Wait for the seeded queue item to appear
  await expect(page.locator('text=Alice E2E')).toBeVisible({ timeout: 10_000 });

  // Click the row to open detail panel
  await page.locator('tr:has-text("Alice E2E")').click();

  // Click Confirm in detail panel
  await page.locator('button:has-text("Confirm")').first().click();

  // Wait for modal and confirm
  await expect(page.locator('div[role="dialog"]')).toBeVisible();
  const [confirmResponse] = await Promise.all([
    page.waitForResponse(
      (resp) =>
        resp.url().includes('/ota/queue/') &&
        resp.url().includes('/confirm') &&
        resp.status() === 201
    ),
    page.locator('div[role="dialog"] button:has-text("Confirm")').click(),
  ]);

  const confirmData = await confirmResponse.json();
  const bookingId = confirmData.booking_id as string;
  expect(bookingId).toBeTruthy();

  // Verify actual booking exists in backend
  const bookingResp = await request.get(`/api/v1/bookings/${bookingId}`, {
    headers: { 'X-Org-ID': '00000000-0000-0000-0000-000000000001' },
  });
  expect(bookingResp.status()).toBe(200);
  const booking = await bookingResp.json();
  expect(booking.status).toBe('confirmed');
});
