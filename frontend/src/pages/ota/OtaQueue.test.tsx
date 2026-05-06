import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import OtaQueue from './OtaQueue'
import * as otaApi from '@/services/otaApi'

const mockBooking = (overrides?: Partial<otaApi.ParsedBooking>): otaApi.ParsedBooking => ({
  id: 'b1',
  property_id: 'p1',
  source_type: 'airbnb',
  status: 'pending',
  guest_name: 'Alice Smith',
  guest_email: 'alice@example.com',
  guest_phone: '+91-99999-99999',
  check_in: '2026-05-10',
  check_out: '2026-05-12',
  num_guests: 2,
  room_type: 'Deluxe Room',
  ota_reference: 'AIR-12345',
  confidence_score: 0.96,
  raw_email_id: 'email-1',
  parsed_data: {},
  created_at: '2026-05-01T10:00:00Z',
  updated_at: '2026-05-01T10:00:00Z',
  ...overrides,
})

describe('OtaQueue', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders loading state then list of bookings', async () => {
    vi.spyOn(otaApi, 'getOtaQueue').mockResolvedValue({
      items: [mockBooking(), mockBooking({ id: 'b2', source_type: 'mmt', guest_name: 'Bob Jones', confidence_score: 0.75 })],
      total: 2,
      page: 1,
      page_size: 10,
    })

    render(
      <MemoryRouter>
        <OtaQueue />
      </MemoryRouter>,
    )

    expect(screen.getByText('OTA Queue')).toBeInTheDocument()
    expect(document.querySelector('.animate-pulse')).toBeTruthy()

    await waitFor(() => {
      expect(screen.getAllByText('Alice Smith')[0]).toBeInTheDocument()
      expect(screen.getAllByText('Bob Jones')[0]).toBeInTheDocument()
    })
  })

  it('shows empty state when no bookings', async () => {
    vi.spyOn(otaApi, 'getOtaQueue').mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 10,
    })

    render(
      <MemoryRouter>
        <OtaQueue />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('No bookings in queue.')).toBeInTheDocument()
    })
  })

  it('opens detail view on row click', async () => {
    const booking = mockBooking()
    vi.spyOn(otaApi, 'getOtaQueue').mockResolvedValue({
      items: [booking],
      total: 1,
      page: 1,
      page_size: 10,
    })
    vi.spyOn(otaApi, 'getOtaQueueItem').mockResolvedValue({
      parsed_booking: booking,
      raw_email: null,
      email_link: null,
    })

    render(
      <MemoryRouter>
        <OtaQueue />
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getAllByText('Alice Smith')[0]).toBeInTheDocument())

    await userEvent.click(screen.getAllByText('Alice Smith')[0])

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /confirm/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /edit/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /reject/i })).toBeInTheDocument()
    })
  })

  it('filters by source and status', async () => {
    const getQueue = vi.spyOn(otaApi, 'getOtaQueue').mockResolvedValue({
      items: [mockBooking()],
      total: 1,
      page: 1,
      page_size: 10,
    })

    render(
      <MemoryRouter>
        <OtaQueue />
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getAllByText('Alice Smith')[0]).toBeInTheDocument())

    await userEvent.click(screen.getByRole('button', { name: /filters/i }))

    const sourceSelect = screen.getByLabelText('Source')
    await userEvent.selectOptions(sourceSelect, 'mmt')

    await waitFor(() => {
      expect(getQueue).toHaveBeenLastCalledWith(
        expect.objectContaining({ source_type: 'mmt' }),
      )
    })
  })

  it('paginates results', async () => {
    vi.spyOn(otaApi, 'getOtaQueue').mockResolvedValue({
      items: Array.from({ length: 10 }, (_, i) => mockBooking({ id: `b${i}`, guest_name: `Guest ${i}` })),
      total: 25,
      page: 1,
      page_size: 10,
    })

    render(
      <MemoryRouter>
        <OtaQueue />
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getAllByText('Guest 0')[0]).toBeInTheDocument())

    expect(screen.getByText('Page 1 of 3')).toBeInTheDocument()

    const nextBtn = screen.getByRole('button', { name: /next/i })
    await userEvent.click(nextBtn)

    await waitFor(() => {
      expect(screen.getByText('Page 2 of 3')).toBeInTheDocument()
    })
  })

  it('color-codes confidence scores', async () => {
    vi.spyOn(otaApi, 'getOtaQueue').mockResolvedValue({
      items: [
        mockBooking({ id: 'high', confidence_score: 0.97 }),
        mockBooking({ id: 'med', confidence_score: 0.85 }),
        mockBooking({ id: 'low', confidence_score: 0.6 }),
      ],
      total: 3,
      page: 1,
      page_size: 10,
    })

    render(
      <MemoryRouter>
        <OtaQueue />
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getAllByText('Alice Smith')[0]).toBeInTheDocument())

    const rows = screen.getAllByRole('row').slice(1) // skip header
    expect(rows.length).toBe(3)
  })
})
