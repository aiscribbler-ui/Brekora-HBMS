import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import PropertyList from '@/pages/properties/PropertyList'
import * as propertyApi from '@/services/propertyApi'

const mockProperties = [
  {
    id: 'prop-1',
    name: 'Sunset Villa',
    address: '123 Beach Road, Goa',
    is_active: true,
    is_archived: false,
    photos: [],
    amenities: ['WiFi', 'Pool'],
  },
  {
    id: 'prop-2',
    name: 'Mountain Retreat',
    address: '456 Hill Station, Himachal',
    is_active: false,
    is_archived: false,
    photos: [],
    amenities: [],
  },
  {
    id: 'prop-3',
    name: 'Old Inn',
    address: '789 City Center',
    is_active: false,
    is_archived: true,
    photos: [],
    amenities: [],
  },
]

const routes = [
  {
    path: '/properties',
    element: <PropertyList />,
  },
  {
    path: '/properties/:id',
    element: <div data-testid="property-detail">Property Detail</div>,
  },
  {
    path: '/properties/new',
    element: <div data-testid="property-new">New Property</div>,
  },
]

function renderWithRouter(initialEntries: string[] = ['/properties']) {
  const router = createMemoryRouter(routes, { initialEntries })
  return { router, ...render(<RouterProvider router={router} />) }
}

describe('PropertyList', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders properties from API', async () => {
    vi.spyOn(propertyApi, 'getProperties').mockResolvedValue(mockProperties)
    renderWithRouter()

    await waitFor(() => {
      expect(screen.getByText('Sunset Villa')).toBeInTheDocument()
    })

    expect(screen.getByText('Mountain Retreat')).toBeInTheDocument()
    expect(screen.getByText('Old Inn')).toBeInTheDocument()
    expect(screen.getByText('2 active properties')).toBeInTheDocument()
  })

  it('shows loading state then properties', async () => {
    vi.spyOn(propertyApi, 'getProperties').mockResolvedValue(mockProperties)
    renderWithRouter()

    expect(document.querySelector('.animate-pulse')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('Sunset Villa')).toBeInTheDocument()
    })
  })

  it('filters properties by search input', async () => {
    vi.spyOn(propertyApi, 'getProperties').mockResolvedValue(mockProperties)
    renderWithRouter()

    await waitFor(() => {
      expect(screen.getByText('Sunset Villa')).toBeInTheDocument()
    })

    const searchInput = screen.getByPlaceholderText('Search by name or address...')
    await userEvent.type(searchInput, 'Mountain')

    expect(screen.queryByText('Sunset Villa')).not.toBeInTheDocument()
    expect(screen.getByText('Mountain Retreat')).toBeInTheDocument()
  })

  it('navigates to property detail on row click', async () => {
    vi.spyOn(propertyApi, 'getProperties').mockResolvedValue(mockProperties)
    const { router } = renderWithRouter()

    await waitFor(() => {
      expect(screen.getByText('Sunset Villa')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByText('Sunset Villa'))

    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/properties/prop-1')
    })
  })

  it('navigates to new property form on Add Property click', async () => {
    vi.spyOn(propertyApi, 'getProperties').mockResolvedValue(mockProperties)
    const { router } = renderWithRouter()

    await waitFor(() => {
      expect(screen.getByText('Add Property')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByText('Add Property'))

    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/properties/new')
    })
  })

  it('displays error message when API fails', async () => {
    vi.spyOn(propertyApi, 'getProperties').mockRejectedValue({
      response: { data: { detail: 'Server error' } },
    })
    renderWithRouter()

    await waitFor(() => {
      expect(screen.getByText('Server error')).toBeInTheDocument()
    })
  })
})
