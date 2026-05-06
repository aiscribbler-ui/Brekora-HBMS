import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  ArrowLeftIcon,
  CheckIcon,
  DocumentTextIcon,
  HomeModernIcon,
  PlusIcon,
  CurrencyDollarIcon,
  CalendarIcon,
  TagIcon,
} from '@heroicons/react/24/outline'
import {
  getPackage,
  createPackage,
  updatePackage,
  getCompositions,
  addComposition,
  removeComposition,
  getPackageAddOns,
  addPackageAddOn,
  removePackageAddOn,
  type Package,
  type PackageComposition,
  type PackageAddOn,
} from '@/services/packageApi'
import { getRoomTypes, type RoomType } from '@/services/propertyApi'
import { isAxiosError } from '@/lib/api'
import RoomCompositionBuilder from '@/components/packages/RoomCompositionBuilder'
import AddOnSelector from '@/components/packages/AddOnSelector'
import PricingRules from '@/components/packages/PricingRules'

const compositionSchema = z.object({
  room_type_id: z.string().min(1, 'Room type is required'),
  quantity: z.coerce.number().int().min(1, 'Quantity must be at least 1'),
  nights: z.coerce.number().int().min(1, 'Nights must be at least 1'),
})

const addOnSchema = z.object({
  add_on_id: z.string().min(1, 'Add-on is required'),
  quantity: z.coerce.number().int().min(1, 'Quantity must be at least 1'),
  is_included: z.boolean(),
})

const packageSchema = z.object({
  property_id: z.string().min(1, 'Property is required'),
  name: z.string().min(1, 'Name is required').max(200, 'Name is too long'),
  description: z.string().optional(),
  status: z.enum(['draft', 'active', 'archived']),
  base_price: z.string().min(1, 'Base price is required'),
  max_occupancy: z.preprocess(
    (val) => (val === '' || val === undefined ? undefined : val),
    z.coerce.number().int().min(1, 'Max occupancy must be at least 1').optional(),
  ),
  cancellation_policy_id: z.string().optional(),
  is_featured: z.boolean(),
  compositions: z.array(compositionSchema).min(1, 'At least one room composition is required'),
  add_ons: z.array(addOnSchema),
  pricing_rules: z.record(z.unknown()).optional(),
  date_constraints: z
    .object({
      start_date: z.string().optional().or(z.literal('')),
      end_date: z.string().optional().or(z.literal('')),
      no_restrictions: z.boolean(),
    })
    .optional(),
})

type PackageFormData = z.infer<typeof packageSchema>

type TabKey = 'basic' | 'composition' | 'addons' | 'pricing' | 'dates'

const tabs: { key: TabKey; label: string; icon: React.ElementType }[] = [
  { key: 'basic', label: 'Basic Info', icon: DocumentTextIcon },
  { key: 'composition', label: 'Room Composition', icon: HomeModernIcon },
  { key: 'addons', label: 'Add-ons', icon: PlusIcon },
  { key: 'pricing', label: 'Pricing Rules', icon: CurrencyDollarIcon },
  { key: 'dates', label: 'Date Constraints', icon: CalendarIcon },
]

export default function PackageBuilder() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isNew = id === 'new'

  const [pkg, setPkg] = useState<Package | null>(null)
  const [loading, setLoading] = useState(!isNew)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<TabKey>('basic')
  const [roomTypes, setRoomTypes] = useState<RoomType[]>([])

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors, isDirty },
  } = useForm<PackageFormData>({
    resolver: zodResolver(packageSchema),
    defaultValues: {
      property_id: '',
      name: '',
      description: '',
      status: 'draft',
      base_price: '',
      max_occupancy: 2,
      cancellation_policy_id: '',
      is_featured: false,
      compositions: [],
      add_ons: [],
      pricing_rules: {},
      date_constraints: { no_restrictions: true },
    },
  })

  const propertyId = watch('property_id')
  const compositions = watch('compositions')
  const addOns = watch('add_ons')
  const pricingRules = watch('pricing_rules')
  const dateConstraints = watch('date_constraints')
  const basePrice = watch('base_price')

  useEffect(() => {
    if (!propertyId) {
      setRoomTypes([])
      return
    }
    let cancelled = false
    getRoomTypes(propertyId)
      .then((data) => {
        if (!cancelled) setRoomTypes(data.filter((r) => r.is_active && !r.is_archived))
      })
      .catch(() => {
        if (!cancelled) setError('Failed to load room types.')
      })
    return () => { cancelled = true }
  }, [propertyId])

  useEffect(() => {
    if (isNew || !id) {
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)

    const load = async () => {
      try {
        const data = await getPackage(id)
        if (cancelled) return
        setPkg(data)

        const existingCompositions: PackageFormData['compositions'] =
          data.compositions.map((c: PackageComposition) => ({
            room_type_id: c.room_type_id,
            quantity: c.quantity,
            nights: c.nights,
          }))

        const existingAddOns: PackageFormData['add_ons'] =
          data.add_ons.map((a: PackageAddOn) => ({
            add_on_id: a.add_on_id,
            quantity: a.quantity,
            is_included: a.is_included,
          }))

        const dc = data.date_constraints
        const hasRestrictions = dc && (dc.start_date || dc.end_date)

        reset({
          property_id: data.property_id,
          name: data.name,
          description: data.description ?? '',
          status: data.status as 'draft' | 'active' | 'archived',
          base_price: data.base_price,
          max_occupancy: data.max_occupancy ?? 2,
          cancellation_policy_id: data.cancellation_policy_id ?? '',
          is_featured: false,
          compositions: existingCompositions,
          add_ons: existingAddOns,
          pricing_rules: (data.dynamic_pricing_rules as Record<string, unknown>) ?? {},
          date_constraints: {
            start_date: (dc?.start_date as string) ?? '',
            end_date: (dc?.end_date as string) ?? '',
            no_restrictions: !hasRestrictions,
          },
        })
      } catch (err) {
        if (!cancelled) {
          if (isAxiosError(err) && err.response?.data?.detail) {
            setError(err.response.data.detail)
          } else {
            setError('Failed to load package.')
          }
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [id, isNew, reset])

  const roomTypeMap = useMemo(() => {
    const map = new Map<string, RoomType>()
    roomTypes.forEach((rt) => map.set(rt.id, rt))
    return map
  }, [roomTypes])

  const pricePreview = useMemo(() => {
    const roomCost = compositions.reduce((sum, comp) => {
      const rt = roomTypeMap.get(comp.room_type_id)
      if (!rt) return sum
      const rate = parseFloat(rt.default_rate) || 0
      return sum + comp.quantity * comp.nights * rate
    }, 0)
    return { roomCost }
  }, [compositions, roomTypeMap])

  const syncCompositions = async (
    packageId: string,
    current: PackageFormData['compositions'],
  ) => {
    if (!isNew && pkg) {
      const existing = await getCompositions(packageId)
      for (const comp of existing) {
        await removeComposition(comp.id)
      }
    }
    for (const comp of current) {
      await addComposition(packageId, {
        room_type_id: comp.room_type_id,
        quantity: comp.quantity,
        nights: comp.nights,
      })
    }
  }

  const syncAddOns = async (
    packageId: string,
    current: PackageFormData['add_ons'],
  ) => {
    if (!isNew && pkg) {
      const existing = await getPackageAddOns(packageId)
      for (const ao of existing) {
        await removePackageAddOn(ao.id)
      }
    }
    for (const ao of current) {
      await addPackageAddOn(packageId, {
        add_on_id: ao.add_on_id,
        quantity: ao.quantity,
        is_included: ao.is_included,
      })
    }
  }

  const onSubmit = async (form: PackageFormData, publish = false) => {
    setError(null)
    setSaving(true)
    try {
      const status = publish ? 'active' : form.status
      const dateConstraints =
        form.date_constraints?.no_restrictions
          ? null
          : {
              start_date: form.date_constraints?.start_date || undefined,
              end_date: form.date_constraints?.end_date || undefined,
            }

      const payload = {
        property_id: form.property_id,
        name: form.name,
        description: form.description || undefined,
        status,
        base_price: form.base_price,
        max_occupancy: form.max_occupancy,
        cancellation_policy_id: form.cancellation_policy_id || undefined,
        dynamic_pricing_rules: form.pricing_rules,
        date_constraints: dateConstraints as Record<string, unknown> | undefined,
      }

      let savedId: string
      if (isNew) {
        const created = await createPackage(payload)
        savedId = created.id
        await syncCompositions(savedId, form.compositions)
        await syncAddOns(savedId, form.add_ons)
      } else {
        await updatePackage(id!, payload)
        savedId = id!
        await syncCompositions(savedId, form.compositions)
        await syncAddOns(savedId, form.add_ons)
        const refreshed = await getPackage(savedId)
        setPkg(refreshed)
        reset({
          property_id: refreshed.property_id,
          name: refreshed.name,
          description: refreshed.description ?? '',
          status: refreshed.status as 'draft' | 'active' | 'archived',
          base_price: refreshed.base_price,
          max_occupancy: refreshed.max_occupancy ?? 2,
          cancellation_policy_id: refreshed.cancellation_policy_id ?? '',
          is_featured: false,
          compositions: refreshed.compositions.map((c) => ({
            room_type_id: c.room_type_id,
            quantity: c.quantity,
            nights: c.nights,
          })),
          add_ons: refreshed.add_ons.map((a) => ({
            add_on_id: a.add_on_id,
            quantity: a.quantity,
            is_included: a.is_included,
          })),
          pricing_rules: (refreshed.dynamic_pricing_rules as Record<string, unknown>) ?? {},
          date_constraints: {
            start_date: (refreshed.date_constraints?.start_date as string) ?? '',
            end_date: (refreshed.date_constraints?.end_date as string) ?? '',
            no_restrictions: !refreshed.date_constraints,
          },
        })
      }

      if (isNew) {
        navigate(`/packages/${savedId}`)
      }
    } catch (err) {
      if (isAxiosError(err) && err.response?.data?.detail) {
        setError(err.response.data.detail)
      } else {
        setError('Failed to save package.')
      }
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto space-y-4">
        <div className="h-8 bg-gray-100 rounded w-1/3 animate-pulse" />
        <div className="h-10 bg-gray-100 rounded w-full animate-pulse" />
        <div className="h-64 bg-gray-100 rounded-lg animate-pulse" />
      </div>
    )
  }

  return (
    <div className="max-w-5xl mx-auto">
      <button
        onClick={() => navigate('/packages')}
        className="inline-flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900 mb-4"
      >
        <ArrowLeftIcon className="h-4 w-4" />
        Back to Packages
      </button>

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
        <h1 className="text-2xl font-bold text-gray-900">
          {isNew ? 'New Package' : pkg?.name}
        </h1>
        <div className="text-sm text-gray-500">
          {isNew ? 'Create a new package' : `Status: ${pkg?.status}`}
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded border border-red-200 text-sm" role="alert">
          {error}
        </div>
      )}

      <div className="mb-4 border-b border-gray-200">
        <nav className="-mb-px flex space-x-4 overflow-x-auto" aria-label="Tabs">
          {tabs.map((tab) => {
            const Icon = tab.icon
            const isActive = activeTab === tab.key
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`
                  inline-flex items-center gap-2 px-3 py-2 border-b-2 text-sm font-medium whitespace-nowrap transition-colors
                  ${
                    isActive
                      ? 'border-brand-500 text-brand-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            )
          })}
        </nav>
      </div>

      <form
        onSubmit={handleSubmit((data) => onSubmit(data, false))}
        className="space-y-6"
      >
        {activeTab === 'basic' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">Basic Information</h2>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="sm:col-span-2">
                  <label htmlFor="name" className="block text-sm font-medium text-gray-700">Package Name</label>
                  <input
                    id="name"
                    type="text"
                    {...register('name')}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                  {errors.name && (
                    <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>
                  )}
                </div>

                <div className="sm:col-span-2">
                  <label htmlFor="description" className="block text-sm font-medium text-gray-700">Description</label>
                  <textarea
                    id="description"
                    rows={3}
                    {...register('description')}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>

                <div>
                  <label htmlFor="status" className="block text-sm font-medium text-gray-700">Status</label>
                  <select
                    id="status"
                    {...register('status')}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  >
                    <option value="draft">Draft</option>
                    <option value="active">Active</option>
                    <option value="archived">Archived</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="base_price" className="block text-sm font-medium text-gray-700">Base Price</label>
                  <div className="mt-1 relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm">₹</span>
                    <input
                      id="base_price"
                      type="text"
                      placeholder="0.00"
                      {...register('base_price')}
                      className="block w-full rounded-md border border-gray-300 pl-7 pr-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                    />
                  </div>
                  {errors.base_price && (
                    <p className="mt-1 text-sm text-red-600">{errors.base_price.message}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="max_occupancy" className="block text-sm font-medium text-gray-700">Max Occupancy</label>
                  <input
                    id="max_occupancy"
                    type="number"
                    min={1}
                    {...register('max_occupancy')}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                  {errors.max_occupancy && (
                    <p className="mt-1 text-sm text-red-600">{errors.max_occupancy.message}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="cancellation_policy_id" className="block text-sm font-medium text-gray-700">
                    Cancellation Policy
                  </label>
                  <select
                    id="cancellation_policy_id"
                    {...register('cancellation_policy_id')}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  >
                    <option value="">Default policy</option>
                    <option value="flexible">Flexible</option>
                    <option value="moderate">Moderate</option>
                    <option value="strict">Strict</option>
                  </select>
                  <p className="mt-1 text-xs text-gray-400">Policy selector stub</p>
                </div>

                <div className="sm:col-span-2 flex items-center gap-3">
                  <input
                    id="is_featured"
                    type="checkbox"
                    {...register('is_featured')}
                    className="h-4 w-4 text-brand-600 border-gray-300 rounded focus:ring-brand-500"
                  />
                  <label htmlFor="is_featured" className="text-sm text-gray-700">Featured package</label>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-3">
              <div className="flex items-center gap-2">
                <TagIcon className="h-5 w-5 text-brand-600" />
                <h2 className="text-lg font-semibold text-gray-900">Price Preview</h2>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="bg-gray-50 rounded-md p-3">
                  <p className="text-xs text-gray-500">Base Price</p>
                  <p className="text-lg font-semibold text-gray-900">₹{parseFloat(basePrice || '0').toFixed(2)}</p>
                </div>
                <div className="bg-gray-50 rounded-md p-3">
                  <p className="text-xs text-gray-500">Estimated Room Cost</p>
                  <p className="text-lg font-semibold text-gray-900">₹{pricePreview.roomCost.toFixed(2)}</p>
                </div>
                <div className="bg-brand-50 rounded-md p-3">
                  <p className="text-xs text-brand-700">Subtotal Preview</p>
                  <p className="text-lg font-semibold text-brand-900">
                    ₹{(parseFloat(basePrice || '0') + pricePreview.roomCost).toFixed(2)}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'composition' && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Room Composition</h2>
            <RoomCompositionBuilder
              propertyId={propertyId || null}
              onPropertyChange={(pid) => {
                setValue('property_id', pid, { shouldValidate: true })
                setValue('compositions', [], { shouldValidate: true })
              }}
              compositions={compositions}
              onChange={(next) => setValue('compositions', next, { shouldValidate: true })}
            />
            {errors.compositions && (
              <p className="mt-2 text-sm text-red-600">{(errors.compositions as { message?: string }).message}</p>
            )}
          </div>
        )}

        {activeTab === 'addons' && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Add-ons</h2>
            <AddOnSelector
              selectedAddOns={addOns}
              onChange={(next) => setValue('add_ons', next, { shouldValidate: true })}
            />
          </div>
        )}

        {activeTab === 'pricing' && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Pricing Rules</h2>
            <PricingRules
              value={pricingRules as unknown as Record<string, unknown>}
              onChange={(next) => setValue('pricing_rules', next as unknown as Record<string, unknown>, { shouldValidate: true })}
            />
          </div>
        )}

        {activeTab === 'dates' && (
          <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">Date Constraints</h2>

            <div className="flex items-center gap-3">
              <input
                id="no_restrictions"
                type="checkbox"
                checked={dateConstraints?.no_restrictions ?? true}
                onChange={(e) =>
                  setValue('date_constraints', {
                    ...dateConstraints,
                    no_restrictions: e.target.checked,
                  })
                }
                className="h-4 w-4 text-brand-600 border-gray-300 rounded focus:ring-brand-500"
              />
              <label htmlFor="no_restrictions" className="text-sm text-gray-700">No date restrictions</label>
            </div>

            {!dateConstraints?.no_restrictions && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="start_date" className="block text-sm font-medium text-gray-700">
                    Eligible From
                  </label>
                  <input
                    id="start_date"
                    type="date"
                    value={dateConstraints?.start_date ?? ''}
                    onChange={(e) =>
                      setValue('date_constraints', {
                        ...(dateConstraints || { no_restrictions: false }),
                        start_date: e.target.value,
                      })
                    }
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>
                <div>
                  <label htmlFor="end_date" className="block text-sm font-medium text-gray-700">
                    Eligible Until
                  </label>
                  <input
                    id="end_date"
                    type="date"
                    value={dateConstraints?.end_date ?? ''}
                    onChange={(e) =>
                      setValue('date_constraints', {
                        ...(dateConstraints || { no_restrictions: false }),
                        end_date: e.target.value,
                      })
                    }
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>
              </div>
            )}
          </div>
        )}

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-2">
          <button
            type="submit"
            disabled={saving || (!isDirty && !isNew)}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-md hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {saving ? 'Saving...' : 'Save as Draft'}
          </button>
          <button
            type="button"
            onClick={handleSubmit((data) => onSubmit(data, true))}
            disabled={saving}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <CheckIcon className="h-4 w-4" />
            {saving ? 'Publishing...' : 'Publish'}
          </button>
          <button
            type="button"
            onClick={() => navigate('/packages')}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-white text-gray-700 border border-gray-300 text-sm font-medium rounded-md hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
