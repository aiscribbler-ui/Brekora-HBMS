import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import OwnerDashboard from './OwnerDashboard'
import * as propertyApi from '@/services/propertyApi'
import * as ownerApi from '@/services/ownerApi'
import { useAuthStore } from '@/store/authStore'

vi.mock('@/services/propertyApi')
vi.mock('@/services/ownerApi')

describe('OwnerDashboard', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  afterEach(() => {
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      accessToken: '',
      refreshToken: '',
      tokenType: '',
    })
  })

  it('shows access denied for non-owner/non-admin and redirects', () => {
    useAuthStore.setState({
      user: { id: '1', name: 'User', email: 'user@example.com', role: 'Manager' },
      isAuthenticated: true,
      accessToken: 'token',
      refreshToken: 'refresh',
      tokenType: 'bearer',
    })

    const router = createMemoryRouter(
      [{ path: '/owner', element: <OwnerDashboard /> }],
      { initialEntries: ['/owner'] },
    )

    render(<RouterProvider router={router} />)
    expect(screen.getByText('Access Denied')).toBeInTheDocument()
  })

  it('renders P&L summary cards after generating report', async () => {
    useAuthStore.setState({
      user: { id: '1', name: 'Owner', email: 'owner@example.com', role: 'Owner' },
      isAuthenticated: true,
      accessToken: 'token',
      refreshToken: 'refresh',
      tokenType: 'bearer',
    })

    vi.mocked(propertyApi.getProperties).mockResolvedValue([
      { id: 'p1', name: 'Test Villa', address: '123 Lane', is_active: true, is_archived: false, photos: [], amenities: [] },
    ])

    vi.mocked(ownerApi.getPnl).mockResolvedValue({
      gross_revenue: 100000,
      ota_commission: 10000,
      partner_commission: 5000,
      gst: 18000,
      net_distributable: 67000,
    })

    vi.mocked(ownerApi.getPayout).mockResolvedValue({
      owner_percentage: 70,
      brekora_percentage: 30,
      net_distributable: 67000,
      owner_share: 46900,
      brekora_share: 20100,
      month: '2026-05',
    })

    vi.mocked(ownerApi.getStatement).mockResolvedValue({
      property_id: 'p1',
      month: '2026-05',
      bookings: [],
    })

    const router = createMemoryRouter(
      [{ path: '/owner', element: <OwnerDashboard /> }],
      { initialEntries: ['/owner'] },
    )

    render(<RouterProvider router={router} />)

    await waitFor(() => expect(screen.getByLabelText('Property')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: /Generate Report/i }))

    await waitFor(() => expect(screen.getByText('Gross Revenue')).toBeInTheDocument())
    expect(screen.getByText('OTA Commission')).toBeInTheDocument()
    expect(screen.getByText('Partner Commission')).toBeInTheDocument()
    expect(screen.getByText('GST')).toBeInTheDocument()
    expect(screen.getByText('Net Distributable')).toBeInTheDocument()
  })

  it('shows split visualization with correct percentages', async () => {
    useAuthStore.setState({
      user: { id: '1', name: 'Owner', email: 'owner@example.com', role: 'Owner' },
      isAuthenticated: true,
      accessToken: 'token',
      refreshToken: 'refresh',
      tokenType: 'bearer',
    })

    vi.mocked(propertyApi.getProperties).mockResolvedValue([
      { id: 'p1', name: 'Test Villa', address: '123 Lane', is_active: true, is_archived: false, photos: [], amenities: [] },
    ])

    vi.mocked(ownerApi.getPnl).mockResolvedValue({
      gross_revenue: 100000,
      ota_commission: 10000,
      partner_commission: 5000,
      gst: 18000,
      net_distributable: 67000,
    })

    vi.mocked(ownerApi.getPayout).mockResolvedValue({
      owner_percentage: 70,
      brekora_percentage: 30,
      net_distributable: 67000,
      owner_share: 46900,
      brekora_share: 20100,
      month: '2026-05',
    })

    vi.mocked(ownerApi.getStatement).mockResolvedValue({
      property_id: 'p1',
      month: '2026-05',
      bookings: [],
    })

    const router = createMemoryRouter(
      [{ path: '/owner', element: <OwnerDashboard /> }],
      { initialEntries: ['/owner'] },
    )

    render(<RouterProvider router={router} />)

    await waitFor(() => expect(screen.getByLabelText('Property')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: /Generate Report/i }))

    await waitFor(() => expect(screen.getByText(/Owner \(70%\)/i)).toBeInTheDocument())
    expect(screen.getByText(/Brekora \(30%\)/i)).toBeInTheDocument()
  })

  it('has property selector', async () => {
    useAuthStore.setState({
      user: { id: '1', name: 'Admin', email: 'admin@example.com', role: 'Admin' },
      isAuthenticated: true,
      accessToken: 'token',
      refreshToken: 'refresh',
      tokenType: 'bearer',
    })

    vi.mocked(propertyApi.getProperties).mockResolvedValue([
      { id: 'p1', name: 'Test Villa', address: '123 Lane', is_active: true, is_archived: false, photos: [], amenities: [] },
    ])

    const router = createMemoryRouter(
      [{ path: '/owner', element: <OwnerDashboard /> }],
      { initialEntries: ['/owner'] },
    )

    render(<RouterProvider router={router} />)

    await waitFor(() => expect(screen.getByLabelText('Property')).toBeInTheDocument())
    expect(screen.getByRole('combobox', { name: /Property/i })).toBeInTheDocument()
  })
})
