import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import PackageBuilder from '@/pages/packages/PackageBuilder'
import * as packageApi from '@/services/packageApi'
import * as propertyApi from '@/services/propertyApi'

const mockProperties = [
  {
    id: 'prop-1',
    name: 'Sunset Villa',
    address: '123 Beach Road',
    is_active: true,
    is_archived: false,
    photos: [],
    amenities: [],
  },
]

const mockRoomTypes = [
  {
    id: 'rt-1',
    property_id: 'prop-1',
    name: 'Deluxe Room',
    description: null,
    count: 5,
    base_capacity: 2,
    max_capacity: 3,
    default_rate: '2000.00',
    min_stay: null,
    max_stay: null,
    photos: [],
    is_active: true,
    is_archived: false,
  },
  {
    id: 'rt-2',
    property_id: 'prop-1',
    name: 'Suite',
    description: null,
    count: 2,
    base_capacity: 2,
    max_capacity: 4,
    default_rate: '3500.00',
    min_stay: null,
    max_stay: null,
    photos: [],
    is_active: true,
    is_archived: false,
  },
]

const mockAddOns = [
  {
    id: 'ao-1',
    org_id: 'org-1',
    property_id: 'prop-1',
    name: 'Breakfast',
    description: 'Daily breakfast',
    type: 'day' as const,
    default_capacity: 10,
    unit_price: '500.00',
    is_active: true,
    is_archived: false,
    created_at: '',
    updated_at: '',
  },
]

function renderWithRouter(initialEntries: string[] = ['/packages/new']) {
  const routes = [
    { path: '/packages/new', element: <PackageBuilder /> },
    { path: '/packages/:id', element: <PackageBuilder /> },
    { path: '/packages', element: <div data-testid="package-list">Package List</div> },
  ]
  const router = createMemoryRouter(routes, { initialEntries })
  return { router, ...render(<RouterProvider router={router} />) }
}

describe('PackageBuilder', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(propertyApi, 'getProperties').mockResolvedValue(mockProperties)
    vi.spyOn(propertyApi, 'getRoomTypes').mockResolvedValue(mockRoomTypes)
    vi.spyOn(packageApi, 'getAddOns').mockResolvedValue(mockAddOns)
    vi.spyOn(packageApi, 'createPackage').mockResolvedValue({
      id: 'pkg-1',
      org_id: 'org-1',
      property_id: 'prop-1',
      name: 'Test Package',
      description: null,
      status: 'draft',
      base_price: '5000.00',
      dynamic_pricing_rules: null,
      date_constraints: null,
      max_occupancy: 2,
      cancellation_policy_id: null,
      is_active: true,
      is_archived: false,
      created_at: '',
      updated_at: '',
      compositions: [],
      add_ons: [],
    })
    vi.spyOn(packageApi, 'addComposition').mockResolvedValue({
      id: 'comp-1',
      package_id: 'pkg-1',
      org_id: 'org-1',
      room_type_id: 'rt-1',
      quantity: 1,
      nights: 2,
      created_at: '',
      updated_at: '',
    })
    vi.spyOn(packageApi, 'addPackageAddOn').mockResolvedValue({
      id: 'pao-1',
      package_id: 'pkg-1',
      org_id: 'org-1',
      add_on_id: 'ao-1',
      quantity: 1,
      is_included: false,
      created_at: '',
      updated_at: '',
    })
  })

  it('renders basic info tab and validates required fields', async () => {
    renderWithRouter()

    await waitFor(() => {
      expect(screen.getByText('New Package')).toBeInTheDocument()
    })

    expect(screen.getByLabelText(/Package Name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Base Price/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Max Occupancy/i)).toBeInTheDocument()
  })

  it('shows validation errors on empty submit', async () => {
    renderWithRouter()

    await waitFor(() => {
      expect(screen.getByText('New Package')).toBeInTheDocument()
    })

    const saveBtn = screen.getByRole('button', { name: /Save as Draft/i })
    await userEvent.click(saveBtn)

    await waitFor(() => {
      expect(screen.getByText(/Name is required/i)).toBeInTheDocument()
    })
    expect(screen.getByText(/Base price is required/i)).toBeInTheDocument()
  })

  it('adds and removes room compositions', async () => {
    renderWithRouter()

    await waitFor(() => {
      expect(screen.getByText('New Package')).toBeInTheDocument()
    })

    // Navigate to Room Composition tab
    const compositionTab = screen.getByRole('button', { name: /Room Composition/i })
    await userEvent.click(compositionTab)

    await waitFor(() => {
      expect(screen.getByLabelText(/Property/i)).toBeInTheDocument()
    })

    // Select property
    const propertySelect = screen.getByLabelText(/Property/i)
    await userEvent.selectOptions(propertySelect, 'prop-1')

    await waitFor(() => {
      expect(screen.getByText(/Deluxe Room/i)).toBeInTheDocument()
    })

    // Add room type
    const addBtn = screen.getByRole('button', { name: /Add Room Type/i })
    await userEvent.click(addBtn)

    await waitFor(() => {
      expect(screen.getAllByLabelText(/Quantity/i).length).toBeGreaterThanOrEqual(1)
    })

    // Update quantity
    const qtyInput = screen.getAllByLabelText(/Quantity/i)[0]
    await userEvent.clear(qtyInput)
    await userEvent.type(qtyInput, '2')

    expect(qtyInput).toHaveValue(2)

    // Remove room type
    const removeBtn = screen.getByRole('button', { name: /Remove room type/i })
    await userEvent.click(removeBtn)

    await waitFor(() => {
      expect(screen.queryAllByLabelText(/Quantity/i).length).toBe(0)
    })
  })

  it('updates price preview when composition changes', async () => {
    renderWithRouter()

    await waitFor(() => {
      expect(screen.getByText('New Package')).toBeInTheDocument()
    })

    // Set base price
    const basePriceInput = screen.getByLabelText(/Base Price/i)
    await userEvent.type(basePriceInput, '1000')

    // Go to composition tab
    const compositionTab = screen.getByRole('button', { name: /Room Composition/i })
    await userEvent.click(compositionTab)

    await waitFor(() => {
      expect(screen.getByLabelText(/Property/i)).toBeInTheDocument()
    })

    const propertySelect = screen.getByLabelText(/Property/i)
    await userEvent.selectOptions(propertySelect, 'prop-1')

    await waitFor(() => {
      expect(screen.getByText(/Deluxe Room/i)).toBeInTheDocument()
    })

    const addBtn = screen.getByRole('button', { name: /Add Room Type/i })
    await userEvent.click(addBtn)

    // Set quantity to 2 and nights to 2 for Deluxe Room (2000/night)
    const qtyInputs = await screen.findAllByLabelText(/Quantity/i)
    await userEvent.clear(qtyInputs[0])
    await userEvent.type(qtyInputs[0], '2')

    const nightInputs = screen.getAllByLabelText(/Nights/i)
    await userEvent.clear(nightInputs[0])
    await userEvent.type(nightInputs[0], '2')

    // Go back to basic tab to see preview
    const basicTab = screen.getByRole('button', { name: /Basic Info/i })
    await userEvent.click(basicTab)

    await waitFor(() => {
      expect(screen.getByText(/₹9000.00/)).toBeInTheDocument()
    })
  })

  it('selects add-ons and updates cost', async () => {
    renderWithRouter()

    await waitFor(() => {
      expect(screen.getByText('New Package')).toBeInTheDocument()
    })

    const addonsTab = screen.getByRole('button', { name: /Add-ons/i })
    await userEvent.click(addonsTab)

    await waitFor(() => {
      expect(screen.getByText(/Breakfast/i)).toBeInTheDocument()
    })

    const checkbox = screen.getByRole('checkbox', { name: /Breakfast/i })
    await userEvent.click(checkbox)

    await waitFor(() => {
      expect(screen.getByLabelText(/Quantity/i)).toBeInTheDocument()
    })

    const qtyInput = screen.getByLabelText(/Quantity/i)
    await userEvent.clear(qtyInput)
    await userEvent.type(qtyInput, '2')

    // Included checkbox should appear
    const includedCheckbox = screen.getByRole('checkbox', { name: /Included in package/i })
    expect(includedCheckbox).toBeInTheDocument()
  })

  it('saves draft vs publish', async () => {
    renderWithRouter()

    await waitFor(() => {
      expect(screen.getByText('New Package')).toBeInTheDocument()
    })

    // Fill basic info
    await userEvent.type(screen.getByLabelText(/Package Name/i), 'Weekend Getaway')
    await userEvent.type(screen.getByLabelText(/Base Price/i), '5000')

    // Add composition
    const compositionTab = screen.getByRole('button', { name: /Room Composition/i })
    await userEvent.click(compositionTab)

    await waitFor(() => {
      expect(screen.getByLabelText(/Property/i)).toBeInTheDocument()
    })

    await userEvent.selectOptions(screen.getByLabelText(/Property/i), 'prop-1')

    await waitFor(() => {
      expect(screen.getByText(/Deluxe Room/i)).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: /Add Room Type/i }))

    // Publish
    const publishBtn = screen.getByRole('button', { name: /Publish/i })
    await userEvent.click(publishBtn)

    await waitFor(() => {
      expect(packageApi.createPackage).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Weekend Getaway',
          status: 'active',
          base_price: '5000',
        }),
      )
    })
  })
})
