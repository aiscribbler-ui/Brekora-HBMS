import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import AdminPanel from './AdminPanel'
import * as adminApi from '@/services/adminApi'
import { useAuthStore } from '@/store/authStore'

vi.mock('@/services/adminApi')

describe('AdminPanel', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  afterEach(() => {
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
    })
  })

  it('shows access denied for non-admin and redirects', () => {
    useAuthStore.setState({
      user: { id: '1', name: 'User', email: 'user@example.com', role: 'Guest' },
      isAuthenticated: true,
    })

    const router = createMemoryRouter(
      [{ path: '/admin/*', element: <AdminPanel /> }],
      { initialEntries: ['/admin'] },
    )

    render(<RouterProvider router={router} />)
    expect(screen.getByText('Access Denied')).toBeInTheDocument()
  })

  it('renders feature flags for admin and toggles a flag', async () => {
    useAuthStore.setState({
      user: { id: '1', name: 'Admin', email: 'admin@example.com', role: 'Admin' },
      isAuthenticated: true,
    })

    vi.mocked(adminApi.fetchFeatureFlags).mockResolvedValue([
      { id: '1', key: 'flag1', value: true, description: 'Test flag' },
    ])
    vi.mocked(adminApi.updateFeatureFlag).mockResolvedValue({
      id: '1',
      key: 'flag1',
      value: false,
      description: 'Test flag',
    })

    const router = createMemoryRouter(
      [{ path: '/admin/*', element: <AdminPanel /> }],
      { initialEntries: ['/admin/feature-flags'] },
    )

    render(<RouterProvider router={router} />)

    await waitFor(() => expect(screen.getByText('flag1')).toBeInTheDocument())
    expect(screen.getByText('Test flag')).toBeInTheDocument()

    const toggle = screen.getByRole('button', { name: /Toggle flag1/i })
    fireEvent.click(toggle)

    await waitFor(() => expect(adminApi.updateFeatureFlag).toHaveBeenCalledWith('1', false))
  })

  it('renders user management table', async () => {
    useAuthStore.setState({
      user: { id: '1', name: 'Admin', email: 'admin@example.com', role: 'Admin' },
      isAuthenticated: true,
    })

    vi.mocked(adminApi.fetchUsers).mockResolvedValue([
      {
        id: '2',
        name: 'Jane Doe',
        email: 'jane@example.com',
        role: 'Manager',
        status: 'active',
      },
    ])

    const router = createMemoryRouter(
      [{ path: '/admin/*', element: <AdminPanel /> }],
      { initialEntries: ['/admin/user-management'] },
    )

    render(<RouterProvider router={router} />)

    await waitFor(() => expect(screen.getByText('Jane Doe')).toBeInTheDocument())
    expect(screen.getByText('jane@example.com')).toBeInTheDocument()
    expect(screen.getByText('Manager')).toBeInTheDocument()
  })
})
