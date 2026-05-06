import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm, FormProvider } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAuth } from '@/hooks/useAuth'
import { hasRole } from '@/lib/roles'
import { getProperties, type Property, type RoomType } from '@/services/propertyApi'
import { getPackages, type Package } from '@/services/packageApi'
import { getRoomAvailability } from '@/services/publicApi'
import {
  initBooking,
  createOrder,
  isConflictError,
  extractConflictAlternatives,
  type ConflictAlternative,
} from '@/services/bookingApi'
import { isAxiosError } from '@/lib/api'
import BookingSteps from '@/components/bookings/BookingSteps'
import GuestDetailsForm from '@/components/bookings/GuestDetailsForm'
import PaymentMethodSelector from '@/components/bookings/PaymentMethodSelector'

const manualBookingSchema = z
  .object({
    propertyId: z.string().min(1, 'Property is required'),
    itemType: z.enum(['room', 'package']),
    itemId: z.string().min(1, 'Item is required'),
    checkIn: z.string().min(1, 'Check-in date is required'),
    checkOut: z.string().min(1, 'Check-out date is required'),
    guests: z.coerce.number().min(1, 'At least 1 guest').max(50, 'Too many guests'),
    guestName: z.string().min(1, 'Guest name is required'),
    guestEmail: z.string().min(1, 'Email is required').email('Invalid email'),
    guestPhone: z.string().min(1, 'Phone is required'),
    guestIdNumber: z.string().min(1, 'ID number is required'),
    source: z.enum(['walk_in', 'phone', 'whatsapp', 'referral']),
    paymentMethod: z.enum(['cash', 'upi', 'card', 'bank_transfer', 'pay_later']),
    promoCode: z.string().optional(),
    addOnSelections: z
      .array(
        z.object({
          add_on_id: z.string(),
          date: z.string(),
          quantity: z.number().min(1),
          slot_time: z.string().optional(),
        }),
      )
      .optional(),
  })
  .refine(
    (data) => {
      if (!data.checkIn || !data.checkOut) return true
      return new Date(data.checkOut) > new Date(data.checkIn)
    },
    {
      message: 'Check-out must be after check-in',
      path: ['checkOut'],
    },
  )

export type ManualBookingFormData = z.infer<typeof manualBookingSchema>

export default function ManualBookingForm() {
  const navigate = useNavigate()
  const { user, isAuthenticated } = useAuth()

  const methods = useForm<ManualBookingFormData>({
    resolver: zodResolver(manualBookingSchema),
    defaultValues: {
      propertyId: '',
      itemType: 'room',
      itemId: '',
      checkIn: '',
      checkOut: '',
      guests: 1,
      guestName: '',
      guestEmail: '',
      guestPhone: '',
      guestIdNumber: '',
      source: 'walk_in',
      paymentMethod: 'cash',
      promoCode: '',
      addOnSelections: [],
    },
  })

  const {
    watch,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
    trigger,
  } = methods

  const [step, setStep] = useState(1)
  const [properties, setProperties] = useState<Property[]>([])
  const [roomTypes, setRoomTypes] = useState<RoomType[]>([])
  const [packages, setPackages] = useState<Package[]>([])
  const [availability, setAvailability] = useState<
    { date: string; available_count: number; total_count: number }[]
  >([])
  const [availabilityWarning, setAvailabilityWarning] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [alternatives, setAlternatives] = useState<ConflictAlternative[] | undefined>(undefined)
  const [bookingResult, setBookingResult] = useState<{
    bookingId: string
    holdExpiresAt: string
    amountBreakdown: import('@/services/bookingApi').AmountBreakdown
  } | null>(null)
  const [loadingAvailability, setLoadingAvailability] = useState(false)
  const idempotencyKey = useRef(crypto.randomUUID())

  const propertyId = watch('propertyId')
  const itemType = watch('itemType')
  const itemId = watch('itemId')
  const checkIn = watch('checkIn')
  const checkOut = watch('checkOut')
  const guests = watch('guests')
  const paymentMethod = watch('paymentMethod')

  useEffect(() => {
    let cancelled = false
    getProperties()
      .then((data) => {
        if (!cancelled) setProperties(data.filter((p) => p.is_active))
      })
      .catch(() => {
        if (!cancelled) setErrorMsg('Failed to load properties.')
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!propertyId) return
    let cancelled = false
    Promise.all([
      import('@/services/propertyApi').then((m) => m.getRoomTypes(propertyId)),
      getPackages(),
    ])
      .then(([rooms, pkgs]) => {
        if (!cancelled) {
          setRoomTypes(rooms.filter((r) => r.is_active))
          setPackages(pkgs.filter((p) => p.property_id === propertyId && p.is_active))
        }
      })
      .catch(() => {
        if (!cancelled) setErrorMsg('Failed to load rooms/packages.')
      })
    return () => {
      cancelled = true
    }
  }, [propertyId])

  useEffect(() => {
    if (!propertyId || !itemId || !checkIn || !checkOut || itemType !== 'room') {
      setAvailability([])
      setAvailabilityWarning(null)
      return
    }
    let cancelled = false
    setLoadingAvailability(true)
    getRoomAvailability({
      property_id: propertyId,
      room_type_id: itemId,
      check_in: checkIn,
      check_out: checkOut,
    })
      .then((data) => {
        if (!cancelled) {
          setAvailability(data.nights)
          const insufficient = data.nights.find((n) => n.available_count < 1)
          if (insufficient) {
            setAvailabilityWarning(
              `Insufficient availability on ${insufficient.date} (${insufficient.available_count} of ${insufficient.total_count} left).`,
            )
          } else {
            setAvailabilityWarning(null)
          }
        }
      })
      .catch(() => {
        if (!cancelled) setAvailabilityWarning('Unable to check live availability.')
      })
      .finally(() => {
        if (!cancelled) setLoadingAvailability(false)
      })
    return () => {
      cancelled = true
    }
  }, [propertyId, itemId, checkIn, checkOut, itemType])

  const selectedItemName = useMemo(() => {
    if (itemType === 'room') {
      return roomTypes.find((r) => r.id === itemId)?.name || ''
    }
    return packages.find((p) => p.id === itemId)?.name || ''
  }, [itemType, itemId, roomTypes, packages])

  const canProceed = useMemo(() => {
    if (step === 1) {
      return !!propertyId && !!itemId && !!checkIn && !!checkOut && guests >= 1
    }
    if (step === 2) {
      return true // validated on submit
    }
    if (step === 3) {
      return true
    }
    return true
  }, [step, propertyId, itemId, checkIn, checkOut, guests])

  const onNext = async () => {
    setErrorMsg(null)
    setAlternatives(undefined)
    const valid = await trigger(
      step === 1
        ? ['propertyId', 'itemType', 'itemId', 'checkIn', 'checkOut', 'guests']
        : step === 2
          ? ['guestName', 'guestEmail', 'guestPhone', 'guestIdNumber']
          : step === 3
            ? ['source', 'paymentMethod']
            : undefined,
    )
    if (!valid) return
    if (step === 1 && availabilityWarning && availability.some((n) => n.available_count < 1)) {
      setErrorMsg('Please select dates with sufficient availability.')
      return
    }
    setStep((s) => Math.min(s + 1, 4))
  }

  const onBack = () => setStep((s) => Math.max(s - 1, 1))

  const onSubmit = async (data: ManualBookingFormData) => {
    setErrorMsg(null)
    setAlternatives(undefined)

    try {
      const initResponse = await initBooking({
        property_id: data.propertyId,
        item_type: data.itemType,
        item_id: data.itemId,
        check_in: data.checkIn,
        check_out: data.checkOut,
        guests: data.guests,
        add_on_selections: data.addOnSelections || null,
        promo_code: data.promoCode || null,
        channel_source: data.source,
        idempotency_key: idempotencyKey.current,
        notes: null,
      })

      setBookingResult({
        bookingId: initResponse.booking_id,
        holdExpiresAt: initResponse.hold_expires_at,
        amountBreakdown: initResponse.amount_breakdown,
      })

      if (data.paymentMethod === 'pay_later') {
        // Pay later: just mark as confirmed manually
        setStep(4)
        return
      }

      // For cash/upi/card/bank_transfer in manual booking, record payment via order creation
      await createOrder(initResponse.booking_id)
      setStep(4)
      return
    } catch (err) {
      if (isConflictError(err)) {
        setErrorMsg(err.response?.data?.detail || 'This item was just booked by someone else.')
        setAlternatives(extractConflictAlternatives(err))
        return
      }
      if (isAxiosError<{ detail?: string }>(err)) {
        setErrorMsg(err.response?.data?.detail || 'Failed to create booking.')
      } else {
        setErrorMsg('An unexpected error occurred.')
      }
    }
  }

  if (!isAuthenticated || !hasRole(user?.role, ['Manager', 'Admin'])) {
    // RequireRole around the route handles the redirect; render nothing while
    // the user shape is reconciling on cold load to avoid a flash of content.
    return null
  }

  return (
    <div className="max-w-4xl mx-auto py-6 px-4">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Create Manual Booking</h1>

      <BookingSteps currentStep={step} />

      {errorMsg && (
        <div className="mt-6 p-3 bg-red-50 text-red-700 rounded border border-red-200 text-sm" role="alert">
          {errorMsg}
        </div>
      )}

      {alternatives && alternatives.length > 0 && (
        <div className="mt-4 p-4 bg-yellow-50 rounded border border-yellow-200">
          <p className="text-sm font-medium text-yellow-800 mb-2">Alternative options:</p>
          <div className="space-y-2">
            {alternatives.map((alt) => (
              <button
                key={alt.id}
                type="button"
                onClick={() => {
                  setValue('itemId', alt.id)
                  setValue('itemType', alt.type)
                  setValue('checkIn', alt.check_in)
                  setValue('checkOut', alt.check_out)
                  setErrorMsg(null)
                  setAlternatives(undefined)
                }}
                className="w-full text-left p-3 bg-white rounded border border-yellow-300 hover:bg-yellow-100 text-sm"
              >
                <span className="font-medium">{alt.name}</span>
                <span className="text-gray-500 ml-2">
                  {alt.check_in} → {alt.check_out} @ ₹{alt.price_per_night}/night ({alt.available_count} available)
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-6">
          {step === 1 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900">Booking Details</h3>

              <div>
                <label htmlFor="propertyId" className="block text-sm font-medium text-gray-700">
                  Property
                </label>
                <select
                  id="propertyId"
                  {...methods.register('propertyId')}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                >
                  <option value="">Select property</option>
                  {properties.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
                {errors.propertyId && (
                  <p className="mt-1 text-sm text-red-600">{errors.propertyId.message}</p>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Item Type</label>
                  <div className="mt-1 flex gap-3">
                    <label className="flex items-center gap-2">
                      <input
                        type="radio"
                        value="room"
                        {...methods.register('itemType')}
                        className="h-4 w-4 text-brand-600 border-gray-300 focus:ring-brand-500"
                      />
                      <span className="text-sm text-gray-700">Room</span>
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="radio"
                        value="package"
                        {...methods.register('itemType')}
                        className="h-4 w-4 text-brand-600 border-gray-300 focus:ring-brand-500"
                      />
                      <span className="text-sm text-gray-700">Package</span>
                    </label>
                  </div>
                </div>

                <div>
                  <label htmlFor="itemId" className="block text-sm font-medium text-gray-700">
                    {itemType === 'room' ? 'Room Type' : 'Package'}
                  </label>
                  <select
                    id="itemId"
                    {...methods.register('itemId')}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  >
                    <option value="">Select {itemType}</option>
                    {itemType === 'room'
                      ? roomTypes.map((r) => (
                          <option key={r.id} value={r.id}>
                            {r.name} (max {r.max_capacity} guests)
                          </option>
                        ))
                      : packages.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.name}
                          </option>
                        ))}
                  </select>
                  {errors.itemId && <p className="mt-1 text-sm text-red-600">{errors.itemId.message}</p>}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label htmlFor="checkIn" className="block text-sm font-medium text-gray-700">
                    Check-in
                  </label>
                  <input
                    id="checkIn"
                    type="date"
                    {...methods.register('checkIn')}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                  {errors.checkIn && <p className="mt-1 text-sm text-red-600">{errors.checkIn.message}</p>}
                </div>
                <div>
                  <label htmlFor="checkOut" className="block text-sm font-medium text-gray-700">
                    Check-out
                  </label>
                  <input
                    id="checkOut"
                    type="date"
                    {...methods.register('checkOut')}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                  {errors.checkOut && <p className="mt-1 text-sm text-red-600">{errors.checkOut.message}</p>}
                </div>
                <div>
                  <label htmlFor="guests" className="block text-sm font-medium text-gray-700">
                    Guests
                  </label>
                  <input
                    id="guests"
                    type="number"
                    min={1}
                    {...methods.register('guests')}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                  {errors.guests && <p className="mt-1 text-sm text-red-600">{errors.guests.message}</p>}
                </div>
              </div>

              {loadingAvailability && (
                <div className="text-sm text-gray-500">Checking live availability...</div>
              )}

              {availabilityWarning && (
                <div className="p-3 bg-yellow-50 text-yellow-800 rounded border border-yellow-200 text-sm">
                  {availabilityWarning}
                </div>
              )}

              {availability.length > 0 && !availabilityWarning && (
                <div className="p-3 bg-green-50 text-green-800 rounded border border-green-200 text-sm">
                  All selected nights are available.
                </div>
              )}
            </div>
          )}

          {step === 2 && <GuestDetailsForm />}

          {step === 3 && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700">Source</label>
                <div className="mt-2 grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {(
                    [
                      { value: 'walk_in', label: 'Walk-in' },
                      { value: 'phone', label: 'Phone' },
                      { value: 'whatsapp', label: 'WhatsApp' },
                      { value: 'referral', label: 'Referral' },
                    ] as const
                  ).map((src) => (
                    <label
                      key={src.value}
                      className={`flex items-center gap-2 rounded-lg border p-3 cursor-pointer ${
                        watch('source') === src.value
                          ? 'border-brand-300 bg-brand-50 ring-1 ring-brand-200'
                          : 'border-gray-200 bg-white'
                      }`}
                    >
                      <input
                        type="radio"
                        value={src.value}
                        {...methods.register('source')}
                        className="h-4 w-4 text-brand-600 border-gray-300 focus:ring-brand-500"
                      />
                      <span className="text-sm text-gray-900">{src.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              <PaymentMethodSelector />

              <div>
                <label htmlFor="promoCode" className="block text-sm font-medium text-gray-700">
                  Promo Code (optional)
                </label>
                <input
                  id="promoCode"
                  type="text"
                  {...methods.register('promoCode')}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900">Review & Confirm</h3>

              {!bookingResult ? (
                <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Property</span>
                    <span className="font-medium">
                      {properties.find((p) => p.id === propertyId)?.name}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Item</span>
                    <span className="font-medium">
                      {selectedItemName} ({itemType})
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Dates</span>
                    <span className="font-medium">
                      {checkIn} → {checkOut}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Guests</span>
                    <span className="font-medium">{guests}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Guest</span>
                    <span className="font-medium">{watch('guestName')}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Source</span>
                    <span className="font-medium">{watch('source')}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Payment</span>
                    <span className="font-medium">{watch('paymentMethod')}</span>
                  </div>
                  {watch('promoCode') && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Promo Code</span>
                      <span className="font-medium">{watch('promoCode')}</span>
                    </div>
                  )}
                  <div className="border-t pt-3 mt-2">
                    <p className="text-gray-500 italic">Price will be calculated on confirmation.</p>
                  </div>
                </div>
              ) : (
                <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-3 text-sm">
                  <div className="flex justify-between text-base font-semibold">
                    <span>Total</span>
                    <span>
                      ₹{bookingResult.amountBreakdown.total_amount.toFixed(2)} {' '}
                      {bookingResult.amountBreakdown.currency}
                    </span>
                  </div>
                  <div className="flex justify-between text-gray-600">
                    <span>Subtotal</span>
                    <span>₹{bookingResult.amountBreakdown.subtotal.toFixed(2)}</span>
                  </div>
                  {bookingResult.amountBreakdown.discount_amount > 0 && (
                    <div className="flex justify-between text-green-600">
                      <span>Discount</span>
                      <span>-₹{bookingResult.amountBreakdown.discount_amount.toFixed(2)}</span>
                    </div>
                  )}
                  <div className="flex justify-between text-gray-600">
                    <span>Tax</span>
                    <span>₹{bookingResult.amountBreakdown.tax_amount.toFixed(2)}</span>
                  </div>
                  <div className="pt-2 text-xs text-gray-500">
                    Booking reference: {bookingResult.bookingId}
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="flex items-center justify-between pt-4 border-t">
            {step > 1 ? (
              <button
                type="button"
                onClick={onBack}
                disabled={isSubmitting}
                className="py-2 px-4 rounded-md border border-gray-300 text-gray-700 hover:bg-gray-50 font-medium text-sm"
              >
                Back
              </button>
            ) : (
              <div />
            )}

            {step < 4 ? (
              <button
                type="button"
                onClick={onNext}
                disabled={!canProceed}
                className="py-2 px-6 rounded-md bg-brand-600 text-white font-medium hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
              >
                Next
              </button>
            ) : (
              <button
                type="submit"
                disabled={isSubmitting}
                className="py-2 px-6 rounded-md bg-brand-600 text-white font-medium hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
              >
                {isSubmitting ? 'Confirming...' : paymentMethod === 'pay_later' ? 'Confirm Pay Later' : 'Confirm & Record Payment'}
              </button>
            )}
          </div>
        </form>
      </FormProvider>
    </div>
  )
}
