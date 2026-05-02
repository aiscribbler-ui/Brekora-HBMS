import { test, expect, type APIRequestContext } from '@playwright/test';

const API_BASE = 'http://localhost:8000/api/v1';
const DEFAULT_ORG_ID = '00000000-0000-0000-0000-000000000001';

function currentMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

function monthDate(day: number): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

async function loginManager(request: APIRequestContext) {
  const res = await request.post(`${API_BASE}/auth/login`, {
    headers: { 'X-Org-ID': DEFAULT_ORG_ID, 'Content-Type': 'application/json' },
    data: {
      email: 'e2e-manager@brekora.test',
      password: 'E2EManager123!',
    },
  });
  expect(res.ok()).toBeTruthy();
  const data = await res.json();
  expect(data.access_token).toBeTruthy();
  return data.access_token as string;
}

async function createProperty(request: APIRequestContext) {
  const res = await request.post(`${API_BASE}/properties`, {
    headers: { 'X-Org-ID': DEFAULT_ORG_ID, 'Content-Type': 'application/json' },
    data: { name: 'E2E Owner P&L Property', address: '123 P&L Lane, Test City' },
  });
  expect(res.ok()).toBeTruthy();
  return res.json();
}

async function createRoomType(request: APIRequestContext, propertyId: string) {
  const res = await request.post(`${API_BASE}/properties/${propertyId}/room-types`, {
    headers: { 'X-Org-ID': DEFAULT_ORG_ID, 'Content-Type': 'application/json' },
    data: {
      name: 'P&L Standard Room',
      count: 10,
      base_capacity: 2,
      max_capacity: 3,
      default_rate: 2000.0,
    },
  });
  expect(res.ok()).toBeTruthy();
  return res.json();
}

async function createConfirmedBooking(
  request: APIRequestContext,
  propertyId: string,
  roomTypeId: string,
  checkIn: string,
  checkOut: string,
  grossAmount: number,
  sourceType: string,
  partnerAttributionId?: string
) {
  const res = await request.post(`${API_BASE}/bookings/`, {
    headers: { 'X-Org-ID': DEFAULT_ORG_ID, 'Content-Type': 'application/json' },
    data: {
      booking_type: 'room',
      source_type: sourceType,
      property_id: propertyId,
      check_in: checkIn,
      check_out: checkOut,
      status: 'confirmed',
      gross_amount: grossAmount,
      total_amount: grossAmount,
      tax_amount: 0,
      discount_amount: 0,
      currency: 'INR',
      partner_attribution_id: partnerAttributionId ?? null,
      line_items_data: [
        {
          item_type: 'room',
          item_id: roomTypeId,
          quantity: 1,
          unit_price: grossAmount,
          nights: 1,
          total_price: grossAmount,
        },
      ],
    },
  });
  expect(res.ok()).toBeTruthy();
  return res.json();
}

test('E2E-004: Owner P&L Test', async ({ page, request }) => {
  test.setTimeout(30_000);
  const month = currentMonth();

  // 1. Setup: create property and room type via API
  const property = await createProperty(request);
  const roomType = await createRoomType(request, property.id);

  // 2. Login as manager to obtain token for owner-report endpoints
  const accessToken = await loginManager(request);
  const authHeaders = {
    Authorization: `Bearer ${accessToken}`,
    'X-Org-ID': DEFAULT_ORG_ID,
    'Content-Type': 'application/json',
  };

  // 3. Create 6 confirmed bookings with deterministic amounts in current month
  const bookings = [
    // direct bookings
    { checkIn: monthDate(10), checkOut: monthDate(11), gross: 1000.00, source: 'direct', partner: undefined },
    { checkIn: monthDate(11), checkOut: monthDate(12), gross: 2000.00, source: 'direct', partner: undefined },
    // OTA bookings (15% commission)
    { checkIn: monthDate(12), checkOut: monthDate(13), gross: 3000.00, source: 'gmail_airbnb', partner: undefined },
    { checkIn: monthDate(13), checkOut: monthDate(14), gross: 4000.00, source: 'gmail_mmt', partner: undefined },
    // manual booking with partner attribution (10% partner commission)
    { checkIn: monthDate(14), checkOut: monthDate(15), gross: 5000.00, source: 'manual', partner: 'e2e-partner-001' },
    // ical OTA booking
    { checkIn: monthDate(15), checkOut: monthDate(16), gross: 2500.00, source: 'ical', partner: undefined },
  ];

  const createdBookings = [];
  for (const b of bookings) {
    const booking = await createConfirmedBooking(
      request,
      property.id,
      roomType.id,
      b.checkIn,
      b.checkOut,
      b.gross,
      b.source,
      b.partner
    );
    createdBookings.push(booking);
  }
  expect(createdBookings.length).toBe(6);

  // 4. Frontend check: /owner page does not exist yet (FE-010 pending)
  //    Skip frontend navigation per task instructions; use API-only verifications.
  const ownerPageRes = await request.get('/owner');
  expect(ownerPageRes.status()).toBe(404);

  // Expected P&L calculations
  const expectedGross = 17500.00; // 1000+2000+3000+4000+5000+2500
  const expectedOtaGross = 9500.00; // 3000+4000+2500
  const expectedOtaCommission = +(expectedOtaGross * 0.15).toFixed(2); // 1425.00
  const expectedPartnerCommission = +(5000.00 * 0.10).toFixed(2); // 500.00
  const expectedNetDistributable = +(expectedGross - expectedOtaCommission - expectedPartnerCommission).toFixed(2); // 15575.00
  const expectedOwnerShare = +(expectedNetDistributable * 0.70).toFixed(2); // 10902.50
  const expectedBrekoraShare = +(expectedNetDistributable * 0.30).toFixed(2); // 4672.50

  // 5. Verify P&L API
  const pnlRes = await request.get(`${API_BASE}/owner/pnl`, {
    headers: authHeaders,
    params: { property_id: property.id, month },
  });
  expect(pnlRes.ok()).toBeTruthy();
  const pnl = await pnlRes.json();

  expect(parseFloat(pnl.gross_amount)).toBeCloseTo(expectedGross, 2);
  expect(parseFloat(pnl.ota_commission)).toBeCloseTo(expectedOtaCommission, 2);
  expect(parseFloat(pnl.partner_commission)).toBeCloseTo(expectedPartnerCommission, 2);
  expect(parseFloat(pnl.net_distributable)).toBeCloseTo(expectedNetDistributable, 2);
  expect(pnl.booking_count).toBe(6);

  // Verify booking breakdown in P&L
  expect(Array.isArray(pnl.booking_breakdown)).toBe(true);
  expect(pnl.booking_breakdown.length).toBe(6);
  const directRows = pnl.booking_breakdown.filter((b: any) => b.source === 'direct');
  const otaRows = pnl.booking_breakdown.filter((b: any) =>
    ['gmail_airbnb', 'gmail_mmt', 'ical'].includes(b.source)
  );
  expect(directRows.length).toBe(2);
  expect(otaRows.length).toBe(3);

  // Verify OTA commission on individual OTA rows
  for (const row of otaRows) {
    const expectedBookingOta = +(parseFloat(row.gross) * 0.15).toFixed(2);
    expect(parseFloat(row.ota_commission)).toBeCloseTo(expectedBookingOta, 2);
  }

  // Verify partner commission on the manual booking
  const manualRow = pnl.booking_breakdown.find((b: any) => b.source === 'manual');
  expect(manualRow).toBeTruthy();
  expect(parseFloat(manualRow.partner_commission)).toBeCloseTo(expectedPartnerCommission, 2);

  // 6. Verify Payout API (70/30 split)
  const payoutRes = await request.get(`${API_BASE}/owner/payout`, {
    headers: authHeaders,
    params: { property_id: property.id, month },
  });
  expect(payoutRes.ok()).toBeTruthy();
  const payout = await payoutRes.json();

  expect(parseFloat(payout.gross_amount)).toBeCloseTo(expectedGross, 2);
  expect(parseFloat(payout.ota_commission)).toBeCloseTo(expectedOtaCommission, 2);
  expect(parseFloat(payout.partner_commission)).toBeCloseTo(expectedPartnerCommission, 2);
  expect(parseFloat(payout.net_distributable)).toBeCloseTo(expectedNetDistributable, 2);
  expect(parseFloat(payout.owner_share)).toBeCloseTo(expectedOwnerShare, 2);
  expect(parseFloat(payout.brekora_share)).toBeCloseTo(expectedBrekoraShare, 2);
  expect(payout.owner_percentage).toBeCloseTo(70.0, 2);
  expect(payout.brekora_percentage).toBeCloseTo(30.0, 2);
  expect(payout.status).toBe('pending');

  // 7. Verify Statement API
  const stmtRes = await request.get(`${API_BASE}/owner/statement`, {
    headers: authHeaders,
    params: { property_id: property.id, month },
  });
  expect(stmtRes.ok()).toBeTruthy();
  const statement = await stmtRes.json();

  // Summary matches payout
  expect(parseFloat(statement.summary.gross_amount)).toBeCloseTo(expectedGross, 2);
  expect(parseFloat(statement.summary.ota_commission)).toBeCloseTo(expectedOtaCommission, 2);
  expect(parseFloat(statement.summary.partner_commission)).toBeCloseTo(expectedPartnerCommission, 2);
  expect(parseFloat(statement.summary.net_distributable)).toBeCloseTo(expectedNetDistributable, 2);
  expect(parseFloat(statement.summary.owner_share)).toBeCloseTo(expectedOwnerShare, 2);
  expect(parseFloat(statement.summary.brekora_share)).toBeCloseTo(expectedBrekoraShare, 2);
  expect(statement.summary.owner_percentage).toBeCloseTo(70.0, 2);
  expect(statement.summary.brekora_percentage).toBeCloseTo(30.0, 2);

  // Chart data present and correct
  expect(statement.chart.labels).toContain('Owner Share');
  expect(statement.chart.labels).toContain('Brekora Share');
  expect(statement.chart.labels).toContain('OTA Commission');
  expect(statement.chart.labels).toContain('Partner Commission');
  const ownerChartIndex = statement.chart.labels.indexOf('Owner Share');
  const brekoraChartIndex = statement.chart.labels.indexOf('Brekora Share');
  expect(parseFloat(statement.chart.values[ownerChartIndex])).toBeCloseTo(expectedOwnerShare, 2);
  expect(parseFloat(statement.chart.values[brekoraChartIndex])).toBeCloseTo(expectedBrekoraShare, 2);

  // Bookings table has correct number of rows with correct sources and amounts
  expect(Array.isArray(statement.bookings)).toBe(true);
  expect(statement.bookings.length).toBe(6);

  for (const expected of bookings) {
    const row = statement.bookings.find((b: any) => b.source === expected.source && parseFloat(b.gross) === expected.gross);
    expect(row).toBeTruthy();
  }
});
