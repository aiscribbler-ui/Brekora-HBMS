import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import PropertyDetail from '@/pages/properties/PropertyDetail'
import * as propertyApi from '@/services/propertyApi'

const mockProperty = {
  id: 'prop-1',
  name: 'Sunset Villa',
  address: '123 Beach Road, Goa',
  gstin: '27AABCU9603R1ZM',
  pan: 'AABCU9603R',
  owner_contact: '+91 98765 43210',
  is_active: true,
  is_archived: false,
  photos: [{ url: 'https://example.com/photo1.jpg', caption: 'Front' }],
  amenities: ['WiFi', 'Pool'],
  default_check_in_time: '14:00',
  default_check_out_time: '11:00',
}

const routes = [
  {
    path: '/properties/:id',
    element: <PropertyDetail />,
  },
  {
    path: '/properties',
    element: <div data-testid="property-list">Property List</div>,
  },
]

function renderWithRouter(initialEntries: string[] = ['/properties/prop-1']) {
  const router = createMemoryRouter(routes, { initialEntries })
  return { router, ...render(<RouterProvider router={router} />) }
}

describe('PropertyDetail', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders property detail and form', async () => {
    vi.spyOn(propertyApi, 'getProperty').mockResolvedValue(mockProperty)
    renderWithRouter()

    await waitFor(() => {
      expect(screen.getByDisplayValue('Sunset Villa')).toBeInTheDocument()
    })

    expect(screen.getByDisplayValue('123 Beach Road, Goa')).toBeInTheDocument()
    expect(screen.getByText('WiFi')).toBeInTheDocument()
    expect(screen.getByText('Pool')).toBeInTheDocument()
  })

  it('updates property on save', async () => {
    vi.spyOn(propertyApi, 'getProperty').mockResolvedValue(mockProperty)
    const updateSpy = vi.spyOn(propertyApi, 'updateProperty').mockResolvedValue({
      ...mockProperty,
      name: 'Updated Villa',
    })

    renderWithRouter()

    await waitFor(() => {
      expect(screen.getByDisplayValue('Sunset Villa')).toBeInTheDocument()
    })

    const nameInput = screen.getByLabelText('Property Name')
    await userEvent.clear(nameInput)
    await userEvent.type(nameInput, 'Updated Villa')

    await userEvent.click(screen.getByRole('button', { name: /save/i }))

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith('prop-1', expect.objectContaining({ name: 'Updated Villa' }))
    })
  })

  it('shows archive confirmation modal and archives property', async () => {
    vi.spyOn(propertyApi, 'getProperty').mockResolvedValue(mockProperty)
    const updateSpy = vi.spyOn(propertyApi, 'updateProperty').mockResolvedValue({
      ...mockProperty,
      is_archived: true,
    })

    renderWithRouter()

    await waitFor(() => {
      expect(screen.getByText('Sunset Villa')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: /archive/i }))

    expect(screen.getByText('Archive Property')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /^confirm$/i }))

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith('prop-1', { is_archived: true })
    })
  })

  it('navigates back to property list on cancel', async () => {
    vi.spyOn(propertyApi, 'getProperty').mockResolvedValue(mockProperty)
    const { router } = renderWithRouter()

    await waitFor(() => {
      expect(screen.getByText('Sunset Villa')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: /cancel/i }))

    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/properties')
    })
  })

  it('creates a new property', async () => {
    const createSpy = vi.spyOn(propertyApi, 'createProperty').mockResolvedValue({
      ...mockProperty,
      id: 'prop-new',
    })

    const { router } = renderWithRouter(['/properties/new'])

    await waitFor(() => {
      expect(screen.getByText('New Property')).toBeInTheDocument()
    })

    await userEvent.type(screen.getByLabelText('Property Name'), 'New Villa')
    await userEvent.type(screen.getByLabelText('Address'), 'New Address')

    await userEvent.click(screen.getByRole('button', { name: /save/i }))

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith(expect.objectContaining({ name: 'New Villa', address: 'New Address' }))
      expect(router.state.location.pathname).toBe('/properties/prop-new')
    })
  })
})
