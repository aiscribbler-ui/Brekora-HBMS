import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import BookingDetail from './BookingDetail'
import * as bookingApi from '@/services/bookingApi'

vi.mock('@/services/bookingApi')

const mockBooking = {
  id: 'booking-123',
  org_id: 'org-1',
  booking_type: 'room',
  source_type: 'direct',
  source_reference: null,
  property_id: 'prop-1',
  guest_id: 'guest-1',
  check_in: '2026-06-01',
  check_out: '2026-06-05',
  status: 'confirmed',
  line_items: [
    {
      item_type: 'room',
      item_id: 'room-1',
      quantity: 1,
      nights: 4,
      unit_price: 2500,
      total_price: 10000,
    },
  ],
  gross_amount: 10000,
  discount_amount: 500,
  tax_amount: 1800,
  total_amount: 11300,
  currency: 'INR',
  cancellation_policy_snapshot: {
    is_non_refundable: false,
    free_cancellation_hours: 48,
    partial_refund_hours: 24,
    partial_refund_percentage: 50,
  },
  partner_attribution_id: null,
  payment_state: 'paid',
  idempotency_key: null,
  notes: 'Late arrival expected.',
  created_at: '2026-05-01T10:00:00Z',
  updated_at: '2026-05-01T10:00:00Z',
  cancelled_at: null,
  cancellation_reason: null,
  modification_log: [
    {
      timestamp: '2026-05-01T12:00:00Z',
      actor_user_id: 'user-1',
      changes: {
        check_in: { old: '2026-06-02', new: '2026-06-01' },
      },
      reason: 'Guest requested earlier date',
    },
  ],
  line_item_records: [],
  guest: {
    name: 'John Doe',
    email: 'john@example.com',
    phone: '+91-9876543210',
    id_number: '1234-5678-9012',
  },
}

describe('BookingDetail', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.useFakeTimers({ shouldAdvanceTime: true })
    vi.setSystemTime(new Date('2026-05-01T00:00:00Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  const setupRouter = () => {
    const router = createMemoryRouter(
      [{ path: '/bookings/:id', element: <BookingDetail /> }],
      { initialEntries: ['/bookings/booking-123'] },
    )
    return render(<RouterProvider router={router} />)
  }

  it('renders booking detail with correct status badge', async () => {
    vi.mocked(bookingApi.getBooking).mockResolvedValue(mockBooking)

    setupRouter()

    await waitFor(() => expect(screen.getByText(/Booking booking-123/i)).toBeInTheDocument())
    expect(screen.getByText('confirmed')).toBeInTheDocument()
    expect(screen.getByText('₹11,300.00 INR')).toBeInTheDocument()
    expect(screen.getByText('John Doe')).toBeInTheDocument()
  })

  it('clicking cancel button opens cancel modal', async () => {
    vi.mocked(bookingApi.getBooking).mockResolvedValue(mockBooking)

    setupRouter()

    await waitFor(() => expect(screen.getByText(/Booking booking-123/i)).toBeInTheDocument())

    const cancelBtn = screen.getByRole('button', { name: /Cancel Booking/i })
    fireEvent.click(cancelBtn)

    expect(screen.getByText(/Cancel Booking/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Reason for cancellation/i)).toBeInTheDocument()
  })

  it('renders modification log entries', async () => {
    vi.mocked(bookingApi.getBooking).mockResolvedValue(mockBooking)

    setupRouter()

    await waitFor(() => expect(screen.getByText(/Modification Log/i)).toBeInTheDocument())

    expect(screen.getByText('Guest requested earlier date')).toBeInTheDocument()

    const summary = screen.getByText('Guest requested earlier date').closest('summary')
    if (summary) fireEvent.click(summary)

    await waitFor(() =>
      expect(screen.getByText(/"2026-06-02"/)).toBeInTheDocument(),
    )
    expect(screen.getByText(/"2026-06-01"/)).toBeInTheDocument()
  })
})
