import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CalendarGrid from '@/pages/calendar/CalendarGrid'

const mockBlockDates = vi.fn()

vi.mock('@/services/calendarApi', async () => {
  const actual = await vi.importActual<typeof import('@/services/calendarApi')>('@/services/calendarApi')
  return {
    ...actual,
    blockDates: (...args: unknown[]) => mockBlockDates(...args),
  }
})

vi.mock('@/hooks/useCalendar', async () => {
  const React = await import('react')
  return {
    useCalendar: () => {
      const [currentMonth, setCurrentMonth] = React.useState(new Date('2026-04-15T00:00:00Z'))
      const [selectedPropertyId, setSelectedPropertyId] = React.useState('p1')
      const [properties] = React.useState([{ id: 'p1', name: 'Sunset Villa', address: 'Goa' }])
      const [roomTypes] = React.useState([
        { id: 'rt1', property_id: 'p1', name: 'Deluxe', count: 4 },
        { id: 'rt2', property_id: 'p1', name: 'Standard', count: 6 },
      ])
      const [availability] = React.useState([
        { room_type_id: 'rt1', available_count: 4, total_count: 4, booked_count: 0, held_count: 0, date: '2026-04-15' },
        { room_type_id: 'rt1', available_count: 2, total_count: 4, booked_count: 1, held_count: 1, date: '2026-04-16' },
        { room_type_id: 'rt1', available_count: 0, total_count: 4, booked_count: 4, held_count: 0, date: '2026-04-17' },
        { room_type_id: 'rt2', available_count: 6, total_count: 6, booked_count: 0, held_count: 0, date: '2026-04-15' },
      ])

      const availabilityMap = React.useMemo(() => {
        const map = new Map<string, import('@/services/calendarApi').CalendarAvailability>()
        for (const a of availability) {
          map.set(`${a.room_type_id}:${a.date}`, a)
        }
        return map
      }, [availability])

      return {
        currentMonth,
        selectedPropertyId,
        properties,
        roomTypes,
        availability,
        availabilityMap,
        isLoading: false,
        error: null,
        goToPrevMonth: () => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1)),
        goToNextMonth: () => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1)),
        goToToday: () => setCurrentMonth(new Date()),
        setSelectedPropertyId,
        refresh: vi.fn(),
        blockDates: mockBlockDates,
      }
    },
  }
})

describe('CalendarGrid', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    vi.setSystemTime(new Date('2026-04-15T00:00:00Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  it('renders with correct month', async () => {
    render(<CalendarGrid />)
    await waitFor(() => {
      expect(screen.getByTestId('month-title')).toHaveTextContent('April 2026')
    })
  })

  it('shows room type rows', async () => {
    render(<CalendarGrid />)
    await waitFor(() => {
      expect(screen.getByText('Deluxe')).toBeInTheDocument()
    })
    expect(screen.getByText('Standard')).toBeInTheDocument()
  })

  it('shows correct color coding for availability', async () => {
    render(<CalendarGrid />)
    await waitFor(() => {
      expect(screen.getByTestId('cell-rt1-2026-04-15')).toBeInTheDocument()
    })

    const cellGreen = screen.getByTestId('cell-rt1-2026-04-15')
    const cellYellow = screen.getByTestId('cell-rt1-2026-04-16')
    const cellRed = screen.getByTestId('cell-rt1-2026-04-17')

    expect(cellGreen.className).toContain('bg-green-100')
    expect(cellYellow.className).toContain('bg-yellow-100')
    expect(cellRed.className).toContain('bg-red-100')
  })

  it('navigates to previous month', async () => {
    render(<CalendarGrid />)
    await waitFor(() => {
      expect(screen.getByTestId('month-title')).toHaveTextContent('April 2026')
    })

    const user = userEvent.setup()
    await user.click(screen.getByTestId('prev-month-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('month-title')).toHaveTextContent('March 2026')
    })
  })

  it('navigates to next month', async () => {
    render(<CalendarGrid />)
    await waitFor(() => {
      expect(screen.getByTestId('month-title')).toHaveTextContent('April 2026')
    })

    const user = userEvent.setup()
    await user.click(screen.getByTestId('next-month-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('month-title')).toHaveTextContent('May 2026')
    })
  })

  it('opens block date modal', async () => {
    render(<CalendarGrid />)
    await waitFor(() => {
      expect(screen.getByTestId('block-dates-btn')).toBeInTheDocument()
    })

    const user = userEvent.setup()
    await user.click(screen.getByTestId('block-dates-btn'))

    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getAllByText('Block Dates').length).toBeGreaterThanOrEqual(1)
  })

  it('opens booking stub modal on cell click', async () => {
    render(<CalendarGrid />)
    await waitFor(() => {
      expect(screen.getByTestId('cell-rt1-2026-04-15')).toBeInTheDocument()
    })

    const user = userEvent.setup()
    await user.click(screen.getByTestId('cell-rt1-2026-04-15'))

    await waitFor(() => {
      expect(screen.getByTestId('booking-modal-rt1-2026-04-15')).toBeInTheDocument()
    })
  })
})
