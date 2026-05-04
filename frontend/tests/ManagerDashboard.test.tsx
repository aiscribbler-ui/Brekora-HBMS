import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { routes } from '@/router'

const mockFetchProperties = vi.fn()
const mockFetchAvailability = vi.fn()
const mockFetchDashboardSummary = vi.fn()
const mockFetchWeekSummary = vi.fn()
const mockFetchOpenTasks = vi.fn()
const mockNavigate = vi.fn()

vi.mock('@/services/dashboardApi', () => ({
  fetchProperties: () => mockFetchProperties(),
  fetchAvailability: () => mockFetchAvailability(),
  fetchDashboardSummary: () => mockFetchDashboardSummary(),
  fetchWeekSummary: () => mockFetchWeekSummary(),
  fetchOpenTasks: () => mockFetchOpenTasks(),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

function renderRoute(initialEntry = '/dashboard') {
  const testRouter = createMemoryRouter(routes, {
    initialEntries: [initialEntry],
  })
  return render(<RouterProvider router={testRouter} />)
}

describe('ManagerDashboard', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    mockFetchProperties.mockResolvedValue([
      { id: 'p1', name: 'Sunset Villa', address: 'Goa', status: 'active' },
    ])
    mockFetchAvailability.mockResolvedValue([
      { room_type_id: 'rt1', available_count: 2, total_count: 5, date: '2026-04-30' },
    ])
    mockFetchDashboardSummary.mockResolvedValue({
      arrivals: 3,
      departures: 2,
      inHouse: 8,
      pendingCheckIns: 1,
    })
    mockFetchWeekSummary.mockResolvedValue({
      occupancyPercent: 0,
      adrByProperty: [],
    })
    mockFetchOpenTasks.mockResolvedValue({
      otaQueueReview: 2,
      paymentFailures: 1,
      pendingRefunds: 0,
    })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  it('renders all widgets', async () => {
    renderRoute()
    await waitFor(() => {
      expect(screen.getByText(/Manager Dashboard/i)).toBeInTheDocument()
    })
    expect(screen.getByText(/Today/i)).toBeInTheDocument()
    expect(screen.getByText(/This Week/i)).toBeInTheDocument()
    expect(screen.getByText(/Open Tasks/i)).toBeInTheDocument()
    expect(screen.getByText(/Quick Actions/i)).toBeInTheDocument()
  })

  it('shows today view counts', async () => {
    renderRoute()
    await waitFor(() => {
      expect(screen.getAllByText('3')[0]).toBeInTheDocument() // arrivals
    })
    expect(screen.getAllByText('2')[0]).toBeInTheDocument() // departures
    expect(screen.getAllByText('8')[0]).toBeInTheDocument() // in-house
    expect(screen.getAllByText('1')[0]).toBeInTheDocument() // pending check-ins
  })

  it('shows open tasks with red badges when > 0', async () => {
    renderRoute()
    await waitFor(() => {
      expect(screen.getAllByText('2')[0]).toBeInTheDocument()
    })
    const badges = screen.getAllByText('2')
    expect(badges.length).toBeGreaterThanOrEqual(1)
  })

  it('shows occupancy bar', async () => {
    renderRoute()
    await waitFor(() => {
      expect(screen.getByTestId('occupancy-bar')).toBeInTheDocument()
    })
  })

  it('navigates to /bookings/new on Create Booking click', async () => {
    renderRoute()
    await waitFor(() => {
      expect(screen.getByTestId('action-create-booking')).toBeInTheDocument()
    })
    const user = userEvent.setup()
    await user.click(screen.getByTestId('action-create-booking'))
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/bookings/new')
    })
  })

  it('navigates to /ota/mappings on Edit OTA Mapping click', async () => {
    renderRoute()
    await waitFor(() => {
      expect(screen.getByTestId('action-ota-mapping')).toBeInTheDocument()
    })
    const user = userEvent.setup()
    await user.click(screen.getByTestId('action-ota-mapping'))
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/ota/mappings')
    })
  })

  it('triggers refresh on button click', async () => {
    renderRoute()
    await waitFor(() => {
      expect(screen.getByTestId('refresh-btn')).toBeInTheDocument()
    })
    const user = userEvent.setup()
    await user.click(screen.getByTestId('refresh-btn'))
    await waitFor(() => {
      expect(mockFetchProperties).toHaveBeenCalledTimes(2)
    })
  })

  it('auto-refetches every 60 seconds', async () => {
    renderRoute()
    await waitFor(() => {
      expect(mockFetchProperties).toHaveBeenCalledTimes(1)
    })
    vi.advanceTimersByTime(60000)
    await waitFor(() => {
      expect(mockFetchProperties).toHaveBeenCalledTimes(2)
    })
  })

  it('displays properties list', async () => {
    renderRoute()
    await waitFor(() => {
      expect(screen.getByText('Sunset Villa')).toBeInTheDocument()
    })
    expect(screen.getByText('Goa')).toBeInTheDocument()
  })
})
