import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { getBooking, modifyBooking, type Booking, type BookingModificationRequest } from '@/services/bookingApi'
import { getRoomTypes, type RoomType } from '@/services/propertyApi'
import { getAddOns, type AddOn } from '@/services/packageApi'
import { isAxiosError } from '@/lib/api'
import BookingSteps from '@/components/bookings/BookingSteps'

const editSchema = z
  .object({
    checkIn: z.string().min(1, 'Check-in date is required'),
    checkOut: z.string().min(1, 'Check-out date is required'),
    roomTypeId: z.string().optional(),
    guestName: z.string().optional(),
    guestEmail: z.string().email('Invalid email').optional().or(z.literal('')),
    guestPhone: z.string().optional(),
    guestIdNumber: z.string().optional(),
    guests: z.coerce.number().min(1, 'At least 1 guest').optional(),
    reason: z.string().min(1, 'Reason is required'),
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

type EditFormData = z.infer<typeof editSchema>

interface EditAddOn {
  add_on_id: string
  date: string
  quantity: number
  slot_time?: string
}

interface ConflictAlt {
  item_type: string
  item_id: string
  item_name: string
  available_count: number
  suggested_price: number
  currency: string
}

export default function BookingEdit() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [booking, setBooking] = useState<Booking | null>(null)
  const [loading, setLoading] = useState(true)
  const [step, setStep] = useState(1)
  const [roomTypes, setRoomTypes] = useState<RoomType[]>([])
  const [addOnsList, setAddOnsList] = useState<AddOn[]>([])
  const [selectedAddOns, setSelectedAddOns] = useState<EditAddOn[]>([])
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [alternatives, setAlternatives] = useState<ConflictAlt[] | undefined>(undefined)
  const [needsOverride, setNeedsOverride] = useState(false)
  const [overrideChecked, setOverrideChecked] = useState(false)
  const [modResult, setModResult] = useState<{
    payment_difference: number
    refund_amount: number | null
    new_total: number
  } | null>(null)

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isSubmitting },
    trigger,
  } = useForm<EditFormData>({
    resolver: zodResolver(editSchema),
    defaultValues: {
      checkIn: '',
      checkOut: '',
      roomTypeId: '',
      guestName: '',
      guestEmail: '',
      guestPhone: '',
      guestIdNumber: '',
      guests: 1,
      reason: 'Guest request',
    },
  })

  useEffect(() => {
    if (!id) return
    let cancelled = false
    setLoading(true)

    Promise.all([
      getBooking(id),
      getAddOns().catch(() => []),
    ])
      .then(([b, addons]) => {
        if (cancelled) return
        setBooking(b)
        setAddOnsList(addons.filter((a) => !a.is_archived))

        setValue('checkIn', b.check_in)
        setValue('checkOut', b.check_out)
        setValue('guests', b.guest?.guests ?? 1)
        if (b.guest) {
          setValue('guestName', b.guest.name || '')
          setValue('guestEmail', b.guest.email || '')
          setValue('guestPhone', b.guest.phone || '')
          setValue('guestIdNumber', b.guest.id_number || '')
          if (b.guest.guests) setValue('guests', b.guest.guests)
        }

        const roomItem = b.line_items?.find(
          (li: Record<string, unknown>) => li.item_type === 'room',
        )
        if (roomItem) {
          setValue('roomTypeId', String(roomItem.item_id))
        }

        const existingAddOns = (b.line_items || [])
          .filter((li: Record<string, unknown>) => li.item_type === 'add_on')
          .map((li: Record<string, unknown>) => ({
            add_on_id: String(li.item_id),
            date: b.check_in,
            quantity: Number(li.quantity) || 1,
            slot_time: '',
          }))
        setSelectedAddOns(existingAddOns)

        return getRoomTypes(b.property_id)
      })
      .then((rooms) => {
        if (!cancelled && rooms) setRoomTypes(rooms.filter((r) => r.is_active))
      })
      .catch(() => {
        if (!cancelled) setErrorMsg('Failed to load booking data.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [id, setValue])

  const checkIn = watch('checkIn')
  const checkOut = watch('checkOut')
  const roomTypeId = watch('roomTypeId')
  const guestName = watch('guestName')
  const guestEmail = watch('guestEmail')
  const guestPhone = watch('guestPhone')
  const guestIdNumber = watch('guestIdNumber')
  const guests = watch('guests')

  const originalValues = useMemo(() => {
    if (!booking) return null
    return {
      checkIn: booking.check_in,
      checkOut: booking.check_out,
      roomTypeId:
        (booking.line_items?.find((li: Record<string, unknown>) => li.item_type === 'room')
          ?.item_id as string) || '',
      guestName: booking.guest?.name || '',
      guestEmail: booking.guest?.email || '',
      guestPhone: booking.guest?.phone || '',
      guestIdNumber: booking.guest?.id_number || '',
      guests: booking.guest?.guests || 1,
      addOns: selectedAddOns,
    }
  }, [booking, selectedAddOns])

  const currentValues = useMemo(
    () => ({
      checkIn,
      checkOut,
      roomTypeId: roomTypeId || '',
      guestName: guestName || '',
      guestEmail: guestEmail || '',
      guestPhone: guestPhone || '',
      guestIdNumber: guestIdNumber || '',
      guests: guests || 1,
      addOns: selectedAddOns,
    }),
    [checkIn, checkOut, roomTypeId, guestName, guestEmail, guestPhone, guestIdNumber, guests, selectedAddOns],
  )

  const changes = useMemo(() => {
    if (!originalValues) return []
    const diffs: { field: string; old: string; new: string }[] = []
    if (originalValues.checkIn !== currentValues.checkIn)
      diffs.push({ field: 'Check-in', old: originalValues.checkIn, new: currentValues.checkIn })
    if (originalValues.checkOut !== currentValues.checkOut)
      diffs.push({ field: 'Check-out', old: originalValues.checkOut, new: currentValues.checkOut })
    if (originalValues.roomTypeId !== currentValues.roomTypeId) {
      const oldName = roomTypes.find((r) => r.id === originalValues.roomTypeId)?.name || originalValues.roomTypeId || 'Current'
      const newName = roomTypes.find((r) => r.id === currentValues.roomTypeId)?.name || currentValues.roomTypeId || 'None'
      diffs.push({ field: 'Room Type', old: oldName, new: newName })
    }
    if (originalValues.guestName !== currentValues.guestName)
      diffs.push({ field: 'Guest Name', old: originalValues.guestName || 'N/A', new: currentValues.guestName || 'N/A' })
    if (originalValues.guestEmail !== currentValues.guestEmail)
      diffs.push({ field: 'Guest Email', old: originalValues.guestEmail || 'N/A', new: currentValues.guestEmail || 'N/A' })
    if (originalValues.guestPhone !== currentValues.guestPhone)
      diffs.push({ field: 'Guest Phone', old: originalValues.guestPhone || 'N/A', new: currentValues.guestPhone || 'N/A' })
    if (originalValues.guestIdNumber !== currentValues.guestIdNumber)
      diffs.push({ field: 'ID Number', old: originalValues.guestIdNumber || 'N/A', new: currentValues.guestIdNumber || 'N/A' })
    if (originalValues.guests !== currentValues.guests)
      diffs.push({ field: 'Guests', old: String(originalValues.guests), new: String(currentValues.guests) })
    if (JSON.stringify(originalValues.addOns) !== JSON.stringify(currentValues.addOns))
      diffs.push({ field: 'Add-ons', old: 'Previous', new: 'Updated' })
    return diffs
  }, [originalValues, currentValues, roomTypes])

  const onNext = async () => {
    setErrorMsg(null)
    setAlternatives(undefined)
    setNeedsOverride(false)
    const valid = await trigger(step === 1 ? ['checkIn', 'checkOut', 'reason'] : ['reason'])
    if (!valid) return
    if (step === 1 && changes.length === 0) {
      setErrorMsg('No changes detected. Please modify at least one field.')
      return
    }
    setStep((s) => Math.min(s + 1, 3))
  }

  const onBack = () => setStep((s) => Math.max(s - 1, 1))

  const onSubmit = async (data: EditFormData) => {
    if (!id) return
    setErrorMsg(null)
    setAlternatives(undefined)

    const payload: BookingModificationRequest = {
      check_in: data.checkIn,
      check_out: data.checkOut,
      room_type_id: data.roomTypeId || undefined,
      add_ons: selectedAddOns.length > 0 ? selectedAddOns : null,
      guest_details: {
        name: data.guestName,
        email: data.guestEmail,
        phone: data.guestPhone,
        id_number: data.guestIdNumber,
        guests: data.guests,
      },
      reason: data.reason,
      override_24h: overrideChecked,
    }

    try {
      const result = await modifyBooking(id, payload)
      setModResult({
        payment_difference: result.payment_difference,
        refund_amount: result.refund_amount,
        new_total: result.new_total,
      })
      setStep(3)
    } catch (err) {
      if (isAxiosError<{ detail?: unknown }>(err) && err.response?.status === 409) {
        const detail = err.response.data.detail
        const alts = Array.isArray(detail)
          ? detail
          : typeof detail === 'object' && detail !== null && 'alternatives' in detail
            ? (detail as Record<string, unknown>).alternatives
            : undefined
        setErrorMsg(
          typeof detail === 'string'
            ? detail
            : typeof detail === 'object' && detail !== null && 'detail' in detail
              ? String((detail as Record<string, unknown>).detail)
              : 'This item was just booked by someone else.',
        )
        setAlternatives(Array.isArray(alts) ? (alts as ConflictAlt[]) : undefined)
        return
      }
      if (isAxiosError<{ detail?: string }>(err) && err.response?.status === 400) {
        const detail = err.response.data.detail || ''
        if (detail.includes('24 hours') || detail.includes('within 24h')) {
          setNeedsOverride(true)
          setErrorMsg(detail)
          return
        }
      }
      if (isAxiosError<{ detail?: string }>(err)) {
        setErrorMsg(err.response?.data?.detail || 'Failed to modify booking.')
      } else {
        setErrorMsg('An unexpected error occurred.')
      }
    }
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto py-6 px-4">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/3" />
          <div className="h-64 bg-gray-200 rounded" />
        </div>
      </div>
    )
  }

  if (!booking) {
    return (
      <div className="max-w-4xl mx-auto py-6 px-4">
        <div className="p-4 bg-red-50 text-red-700 rounded border border-red-200" role="alert">
          {errorMsg || 'Booking not found.'}
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto py-6 px-4">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Edit Booking</h1>

      <BookingSteps currentStep={step} steps={['Edit Details', 'Review Changes', 'Payment']} />

      {errorMsg && (
        <div className="mt-6 p-3 bg-red-50 text-red-700 rounded border border-red-200 text-sm" role="alert">
          {errorMsg}
        </div>
      )}

      {needsOverride && (
        <div className="mt-4 p-4 bg-warning-light rounded border border-warning">
          <p className="text-sm text-warning-dark mb-2">
            This booking is within 24 hours of check-in. Manager override is required to proceed.
          </p>
          <label className="flex items-center gap-2 text-sm text-warning-dark">
            <input
              type="checkbox"
              checked={overrideChecked}
              onChange={(e) => setOverrideChecked(e.target.checked)}
              className="h-4 w-4 text-brand-600 border-gray-300 rounded focus:ring-brand-500"
            />
            I am an admin/manager overriding the 24h policy
          </label>
        </div>
      )}

      {alternatives && alternatives.length > 0 && (
        <div className="mt-4 p-4 bg-warning-light rounded border border-warning">
          <p className="text-sm font-medium text-warning-dark mb-2">Alternative options:</p>
          <div className="space-y-2">
            {alternatives.map((alt) => (
              <button
                key={alt.item_id}
                type="button"
                onClick={() => {
                  setValue('roomTypeId', alt.item_id)
                  setErrorMsg(null)
                  setAlternatives(undefined)
                }}
                className="w-full text-left p-3 bg-white rounded border border-warning hover:bg-warning-light text-sm"
              >
                <span className="font-medium">{alt.item_name}</span>
                <span className="text-gray-500 ml-2">
                  {alt.item_type} @ ₹{alt.suggested_price} ({alt.available_count} available)
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-6">
        {step === 1 && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="checkIn" className="block text-sm font-medium text-gray-700">
                  Check-in
                </label>
                <input
                  id="checkIn"
                  type="date"
                  {...register('checkIn')}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
                {errors.checkIn && (
                  <p className="mt-1 text-sm text-red-600">{errors.checkIn.message}</p>
                )}
              </div>
              <div>
                <label htmlFor="checkOut" className="block text-sm font-medium text-gray-700">
                  Check-out
                </label>
                <input
                  id="checkOut"
                  type="date"
                  {...register('checkOut')}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
                {errors.checkOut && (
                  <p className="mt-1 text-sm text-red-600">{errors.checkOut.message}</p>
                )}
              </div>
            </div>

            <div>
              <label htmlFor="roomTypeId" className="block text-sm font-medium text-gray-700">
                Room Type
              </label>
              <select
                id="roomTypeId"
                {...register('roomTypeId')}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                <option value="">Keep current</option>
                {roomTypes.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} (max {r.max_capacity} guests)
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="guestName" className="block text-sm font-medium text-gray-700">
                  Guest Name
                </label>
                <input
                  id="guestName"
                  type="text"
                  {...register('guestName')}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>
              <div>
                <label htmlFor="guestEmail" className="block text-sm font-medium text-gray-700">
                  Guest Email
                </label>
                <input
                  id="guestEmail"
                  type="email"
                  {...register('guestEmail')}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
                {errors.guestEmail && (
                  <p className="mt-1 text-sm text-red-600">{errors.guestEmail.message}</p>
                )}
              </div>
              <div>
                <label htmlFor="guestPhone" className="block text-sm font-medium text-gray-700">
                  Guest Phone
                </label>
                <input
                  id="guestPhone"
                  type="tel"
                  {...register('guestPhone')}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>
              <div>
                <label htmlFor="guestIdNumber" className="block text-sm font-medium text-gray-700">
                  ID Number
                </label>
                <input
                  id="guestIdNumber"
                  type="text"
                  {...register('guestIdNumber')}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>
              <div>
                <label htmlFor="guests" className="block text-sm font-medium text-gray-700">
                  Guests
                </label>
                <input
                  id="guests"
                  type="number"
                  min={1}
                  {...register('guests')}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
                {errors.guests && (
                  <p className="mt-1 text-sm text-red-600">{errors.guests.message}</p>
                )}
              </div>
              <div>
                <label htmlFor="reason" className="block text-sm font-medium text-gray-700">
                  Reason for Change *
                </label>
                <input
                  id="reason"
                  type="text"
                  {...register('reason')}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
                {errors.reason && (
                  <p className="mt-1 text-sm text-red-600">{errors.reason.message}</p>
                )}
              </div>
            </div>

            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">Add-ons</h3>
              {selectedAddOns.length === 0 && (
                <p className="text-sm text-gray-500">No add-ons selected.</p>
              )}
              <div className="space-y-2">
                {selectedAddOns.map((addon, idx) => (
                  <div key={idx} className="flex items-center gap-2 bg-gray-50 rounded p-2">
                    <select
                      value={addon.add_on_id}
                      onChange={(e) => {
                        const next = [...selectedAddOns]
                        next[idx] = { ...next[idx], add_on_id: e.target.value }
                        setSelectedAddOns(next)
                      }}
                      className="block w-48 rounded-md border border-gray-300 px-2 py-1 text-sm"
                    >
                      {addOnsList.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.name}
                        </option>
                      ))}
                    </select>
                    <input
                      type="date"
                      value={addon.date}
                      onChange={(e) => {
                        const next = [...selectedAddOns]
                        next[idx] = { ...next[idx], date: e.target.value }
                        setSelectedAddOns(next)
                      }}
                      className="block rounded-md border border-gray-300 px-2 py-1 text-sm"
                    />
                    <input
                      type="number"
                      min={1}
                      value={addon.quantity}
                      onChange={(e) => {
                        const next = [...selectedAddOns]
                        next[idx] = { ...next[idx], quantity: parseInt(e.target.value) || 1 }
                        setSelectedAddOns(next)
                      }}
                      className="block w-20 rounded-md border border-gray-300 px-2 py-1 text-sm"
                    />
                    <button
                      type="button"
                      onClick={() =>
                        setSelectedAddOns(selectedAddOns.filter((_, i) => i !== idx))
                      }
                      className="text-red-600 hover:text-red-800 text-sm"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
              <button
                type="button"
                onClick={() =>
                  setSelectedAddOns([
                    ...selectedAddOns,
                    {
                      add_on_id: addOnsList[0]?.id || '',
                      date: checkIn || new Date().toISOString().slice(0, 10),
                      quantity: 1,
                      slot_time: '',
                    },
                  ])
                }
                className="mt-2 text-sm text-brand-600 hover:text-brand-700 font-medium"
              >
                + Add Add-on
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-900">Review Changes</h3>
            {changes.length === 0 ? (
              <p className="text-sm text-gray-500">No changes detected.</p>
            ) : (
              <div className="space-y-2">
                {changes.map((c, idx) => (
                  <div
                    key={idx}
                    className="grid grid-cols-3 gap-2 bg-gray-50 rounded p-3 text-sm"
                  >
                    <div className="font-medium text-gray-700">{c.field}</div>
                    <div className="text-red-600 line-through">{c.old}</div>
                    <div className="text-success font-medium">{c.new}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-900">Modification Result</h3>
            {modResult ? (
              <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">New Total</span>
                  <span className="font-medium text-gray-900">
                    ₹{modResult.new_total.toFixed(2)}
                  </span>
                </div>
                {modResult.payment_difference > 0 && (
                  <div className="p-3 bg-warning-light text-warning-dark rounded border border-warning">
                    <p className="font-medium">
                      Additional payment required: ₹{modResult.payment_difference.toFixed(2)}
                    </p>
                    <button
                      type="button"
                      onClick={() => alert('Razorpay payment flow would open here.')}
                      className="mt-2 inline-flex items-center px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-md hover:bg-brand-700 transition-colors"
                    >
                      Pay Difference
                    </button>
                  </div>
                )}
                {modResult.payment_difference < 0 && (
                  <div className="p-3 bg-success-light text-success-dark rounded border border-success">
                    <p className="font-medium">
                      Refund pending: ₹
                      {(
                        modResult.refund_amount ?? Math.abs(modResult.payment_difference)
                      ).toFixed(2)}
                    </p>
                    <p className="text-xs mt-1">
                      The refund will be processed to the original payment method.
                    </p>
                  </div>
                )}
                {modResult.payment_difference === 0 && (
                  <div className="p-3 bg-success-light text-success-dark rounded border border-success">
                    <p className="font-medium">
                      No payment difference. Booking updated successfully.
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-gray-500">Submit to see the modification result.</p>
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
            <button
              type="button"
              onClick={() => navigate(`/bookings/${id}`)}
              className="py-2 px-4 rounded-md border border-gray-300 text-gray-700 hover:bg-gray-50 font-medium text-sm"
            >
              Cancel
            </button>
          )}

          {step < 3 ? (
            step === 2 ? (
              <button
                type="submit"
                disabled={isSubmitting}
                className="py-2 px-6 rounded-md bg-brand-600 text-white font-medium hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
              >
                {isSubmitting ? 'Submitting...' : 'Confirm Changes'}
              </button>
            ) : (
              <button
                type="button"
                onClick={onNext}
                className="py-2 px-6 rounded-md bg-brand-600 text-white font-medium hover:bg-brand-700 text-sm"
              >
                Next
              </button>
            )
          ) : (
            <button
              type="button"
              onClick={() => navigate(`/bookings/${id}`)}
              className="py-2 px-6 rounded-md bg-brand-600 text-white font-medium hover:bg-brand-700 text-sm"
            >
              Done
            </button>
          )}
        </div>
      </form>
    </div>
  )
}
