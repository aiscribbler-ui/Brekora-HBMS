import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { initBooking, createOrder } from '@/services/publicApi'
import { isConflictError, extractConflictAlternatives } from '@/services/bookingApi'
import { isAxiosError } from '@/lib/api'
import ConflictBanner from '@/components/public/ConflictBanner'
import type { ConflictAlternative } from '@/services/bookingApi'

const bookingFlowSchema = z.object({
  guestName: z.string().min(1, 'Full name is required'),
  guestEmail: z.string().min(1, 'Email is required').email('Invalid email'),
  guestPhone: z.string().min(1, 'Phone is required'),
  promoCode: z.string().optional(),
})

type BookingFlowData = z.infer<typeof bookingFlowSchema>

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => {
      open: () => void
      on: (event: string, handler: () => void) => void
    }
  }
}

export default function BookingFlow() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const propertyId = searchParams.get('property_id') || ''
  const itemId = searchParams.get('item_id') || ''
  const itemType = (searchParams.get('item_type') as 'room' | 'package') || 'room'
  const checkIn = searchParams.get('check_in') || ''
  const checkOut = searchParams.get('check_out') || ''
  const guestsParam = searchParams.get('guests') || '2'
  const guests = parseInt(guestsParam) || 2
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
    trigger,
  } = useForm<BookingFlowData>({
    resolver: zodResolver(bookingFlowSchema),
    defaultValues: {
      guestName: '',
      guestEmail: '',
      guestPhone: '',
      promoCode: '',
    },
  })

  const [step, setStep] = useState(1)
  const [bookingResult, setBookingResult] = useState<{
    bookingId: string
    holdExpiresAt: string
    amountBreakdown: import('@/services/publicApi').PriceBreakdown
  } | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [alternatives, setAlternatives] = useState<ConflictAlternative[] | undefined>(undefined)
  const [razorpayLoaded, setRazorpayLoaded] = useState(false)
  const idempotencyKey = useRef(crypto.randomUUID())

  const promoCode = watch('promoCode')

  const scriptRef = useRef<HTMLScriptElement | null>(null)

  useEffect(() => {
    if (scriptRef.current) return
    const existing = document.querySelector('script[src="https://checkout.razorpay.com/v1/checkout.js"]')
    if (existing) {
      setRazorpayLoaded(true)
      return
    }
    const script = document.createElement('script')
    script.src = 'https://checkout.razorpay.com/v1/checkout.js'
    script.async = true
    script.onload = () => setRazorpayLoaded(true)
    script.onerror = () => setRazorpayLoaded(false)
    document.body.appendChild(script)
    scriptRef.current = script
    return () => {
      if (scriptRef.current && scriptRef.current.parentNode) {
        scriptRef.current.parentNode.removeChild(scriptRef.current)
      }
    }
  }, [])

  const steps = ['Details', 'Review', 'Payment']

  const canProceed = useMemo(() => {
    if (step === 1) {
      return !!watch('guestName') && !!watch('guestEmail') && !!watch('guestPhone')
    }
    return true
  }, [step, watch])

  const onNext = async () => {
    setErrorMsg(null)
    setAlternatives(undefined)
    if (step === 1) {
      const valid = await trigger(['guestName', 'guestEmail', 'guestPhone'])
      if (!valid) return
    }
    if (step === 2) {
      // Initialize booking to hold inventory
      try {
        const data = await initBooking({
          property_id: propertyId,
          item_type: itemType,
          item_id: itemId,
          check_in: checkIn,
          check_out: checkOut,
          guests,
          promo_code: promoCode || null,
          channel_source: 'direct',
          idempotency_key: idempotencyKey.current,
        })
        setBookingResult({
          bookingId: data.booking_id,
          holdExpiresAt: data.hold_expires_at,
          amountBreakdown: data.amount_breakdown,
        })
      } catch (err) {
        if (isConflictError(err)) {
          setErrorMsg(err.response?.data?.detail || 'This item was just booked by someone else.')
          setAlternatives(extractConflictAlternatives(err))
          return
        }
        if (isAxiosError<{ detail?: string }>(err)) {
          setErrorMsg(err.response?.data?.detail || 'Failed to hold inventory.')
        } else {
          setErrorMsg('An unexpected error occurred.')
        }
        return
      }
    }
    setStep((s) => Math.min(s + 1, 3))
  }

  const onBack = () => setStep((s) => Math.max(s - 1, 1))

  const openRazorpay = async (data: BookingFlowData) => {
    setErrorMsg(null)
    if (!bookingResult) return

    try {
      const order = await createOrder(bookingResult.bookingId)
      if (!window.Razorpay) {
        setErrorMsg('Payment gateway not loaded. Please refresh and try again.')
        return
      }
      const options = {
        key: import.meta.env.VITE_RAZORPAY_KEY_ID || '',
        amount: order.amount,
        currency: order.currency,
        name: 'Brekora',
        description: `Booking ${bookingResult.bookingId.slice(0, 8)}`,
        order_id: order.order_id,
        handler: () => {
          navigate(`/book/confirm?booking_id=${bookingResult.bookingId}`)
        },
        prefill: {
          name: data.guestName,
          email: data.guestEmail,
          contact: data.guestPhone,
        },
        theme: {
          color: '#2563eb',
        },
      }
      const rzp = new window.Razorpay(options)
      rzp.on('payment.failed', () => {
        setErrorMsg('Payment failed. You can retry from your guest dashboard.')
      })
      rzp.open()
    } catch (err) {
      if (isAxiosError<{ detail?: string }>(err)) {
        setErrorMsg(err.response?.data?.detail || 'Payment initiation failed.')
      } else {
        setErrorMsg('Payment initiation failed.')
      }
    }
  }

  const onSubmit = (data: BookingFlowData) => {
    if (step === 3) {
      openRazorpay(data)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
          <a href="/book" className="text-xl font-bold text-brand-600">
            Brekora
          </a>
          <span className="text-sm text-gray-500">Book your stay</span>
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">Complete Your Booking</h1>
        <div className="mb-6">
          <div className="flex items-center justify-between">
            {steps.map((label, idx) => {
              const num = idx + 1
              const active = num === step
              const done = num < step
              return (
                <div key={label} className="flex-1 flex flex-col items-center relative">
                  {idx > 0 && (
                    <div
                      className={`absolute left-0 top-4 -translate-x-1/2 w-full h-0.5 ${
                        done || active ? 'bg-brand-600' : 'bg-gray-200'
                      }`}
                      style={{ width: 'calc(100% - 2rem)', left: '-50%' }}
                    />
                  )}
                  <div
                    aria-current={active ? 'step' : undefined}
                    className={`z-10 flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium border-2 ${
                      done
                        ? 'bg-brand-600 border-brand-600 text-white'
                        : active
                          ? 'bg-white border-brand-600 text-brand-600'
                          : 'bg-white border-gray-300 text-gray-400'
                    }`}
                  >
                    {done ? (
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    ) : (
                      num
                    )}
                  </div>
                  <span
                    className={`mt-2 text-xs font-medium ${
                      active ? 'text-brand-600' : done ? 'text-gray-700' : 'text-gray-400'
                    }`}
                    aria-current={active ? 'step' : undefined}
                  >
                    {label}
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        {errorMsg && (
          <div className="mb-4" role="alert">
            {alternatives ? (
              <ConflictBanner
                message={errorMsg}
                alternatives={alternatives}
                onSelectAlternative={(alt) => {
                  const sp = new URLSearchParams(searchParams)
                  sp.set('item_id', alt.id)
                  sp.set('item_type', alt.type)
                  sp.set('check_in', alt.check_in)
                  sp.set('check_out', alt.check_out)
                  navigate(`/book/flow?${sp.toString()}`, { replace: true })
                  setErrorMsg(null)
                  setAlternatives(undefined)
                }}
              />
            ) : (
              <div className="p-3 bg-red-50 text-red-700 rounded border border-red-200 text-sm">
                {errorMsg}
              </div>
            )}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {step === 1 && (
            <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">Guest Details</h2>
              <div>
                <label htmlFor="guestName" className="block text-sm font-medium text-gray-700">
                  Full Name
                </label>
                <input
                  id="guestName"
                  type="text"
                  autoComplete="name"
                  aria-invalid={errors.guestName ? 'true' : 'false'}
                  aria-describedby={errors.guestName ? 'guestName-error' : undefined}
                  {...register('guestName')}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
                {errors.guestName && (
                  <p className="mt-1 text-sm text-red-600" id="guestName-error" role="alert">{errors.guestName.message}</p>
                )}
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="guestEmail" className="block text-sm font-medium text-gray-700">
                    Email
                  </label>
                  <input
                    id="guestEmail"
                    type="email"
                    autoComplete="email"
                    aria-invalid={errors.guestEmail ? 'true' : 'false'}
                    aria-describedby={errors.guestEmail ? 'guestEmail-error' : undefined}
                    {...register('guestEmail')}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                  {errors.guestEmail && (
                    <p className="mt-1 text-sm text-red-600" id="guestEmail-error" role="alert">{errors.guestEmail.message}</p>
                  )}
                </div>
                <div>
                  <label htmlFor="guestPhone" className="block text-sm font-medium text-gray-700">
                    Phone
                  </label>
                  <input
                    id="guestPhone"
                    type="tel"
                    autoComplete="tel"
                    aria-invalid={errors.guestPhone ? 'true' : 'false'}
                    aria-describedby={errors.guestPhone ? 'guestPhone-error' : undefined}
                    {...register('guestPhone')}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                  {errors.guestPhone && (
                    <p className="mt-1 text-sm text-red-600" id="guestPhone-error" role="alert">{errors.guestPhone.message}</p>
                  )}
                </div>
              </div>
              <div>
                <label htmlFor="promoCode" className="block text-sm font-medium text-gray-700">
                  Promo Code (optional)
                </label>
                <input
                  id="promoCode"
                  type="text"
                  {...register('promoCode')}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">Review Booking</h2>
              <div className="text-sm space-y-2">
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
                {watch('promoCode') && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Promo Code</span>
                    <span className="font-medium">{watch('promoCode')}</span>
                  </div>
                )}
              </div>

              {bookingResult ? (
                <div className="border-t pt-3 space-y-2">
                  <div className="flex justify-between text-base font-semibold">
                    <span>Total</span>
                    <span>
                      ₹{bookingResult.amountBreakdown.total_amount.toFixed(2)} {' '}
                      {bookingResult.amountBreakdown.currency}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm text-gray-600">
                    <span>Subtotal</span>
                    <span>₹{bookingResult.amountBreakdown.subtotal.toFixed(2)}</span>
                  </div>
                  {bookingResult.amountBreakdown.discount_amount > 0 && (
                    <div className="flex justify-between text-sm text-green-600">
                      <span>Discount</span>
                      <span>-₹{bookingResult.amountBreakdown.discount_amount.toFixed(2)}</span>
                    </div>
                  )}
                  <div className="flex justify-between text-sm text-gray-600">
                    <span>Tax</span>
                    <span>₹{bookingResult.amountBreakdown.tax_amount.toFixed(2)}</span>
                  </div>
                  <div className="text-xs text-gray-500 pt-1">
                    Hold expires at {new Date(bookingResult.holdExpiresAt).toLocaleString()}
                  </div>
                </div>
              ) : (
                <div className="border-t pt-3 text-sm text-gray-500 italic">
                  Click next to calculate pricing and hold your selection.
                </div>
              )}
            </div>
          )}

          {step === 3 && (
            <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4" aria-label="Razorpay payment region">
              <h2 className="text-lg font-semibold text-gray-900">Payment</h2>
              {bookingResult && (
                <div className="text-sm space-y-2">
                  <div className="flex justify-between text-base font-semibold">
                    <span>Amount to pay</span>
                    <span>
                      ₹{bookingResult.amountBreakdown.total_amount.toFixed(2)} {' '}
                      {bookingResult.amountBreakdown.currency}
                    </span>
                  </div>
                </div>
              )}
              {!razorpayLoaded && (
                <div className="p-3 bg-yellow-50 text-yellow-800 rounded border border-yellow-200 text-sm">
                  Loading payment gateway...
                </div>
              )}
            </div>
          )}

          <div className="flex items-center justify-between pt-2">
            {step > 1 ? (
              <button
                type="button"
                onClick={onBack}
                disabled={isSubmitting}
                className="py-2 px-4 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 font-medium text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
              >
                Back
              </button>
            ) : (
              <div />
            )}
            {step < 3 ? (
              <button
                type="button"
                onClick={onNext}
                disabled={!canProceed || isSubmitting}
                className="py-2 px-6 rounded-lg bg-brand-600 text-white font-medium hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
              >
                {isSubmitting ? 'Please wait...' : step === 2 ? 'Hold & Continue' : 'Next'}
              </button>
            ) : (
              <button
                type="submit"
                disabled={isSubmitting || !razorpayLoaded}
                className="py-2 px-6 rounded-lg bg-brand-600 text-white font-medium hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
              >
                {isSubmitting ? 'Processing...' : 'Pay Now'}
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  )
}
