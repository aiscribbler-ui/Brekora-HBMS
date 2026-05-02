import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

export default function BookingConfirmation() {
  const [searchParams] = useSearchParams()
  const bookingId = searchParams.get('booking_id') || ''
  const [countdown, setCountdown] = useState(10)

  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown((c) => {
        if (c <= 1) {
          clearInterval(timer)
          return 0
        }
        return c - 1
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-white rounded-xl shadow-lg border border-gray-200 p-8 text-center">
        <div className="mx-auto h-12 w-12 bg-green-100 rounded-full flex items-center justify-center mb-4">
          <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>

        <h1 className="text-2xl font-bold text-gray-900 mb-2">Booking Confirmed!</h1>
        <p className="text-gray-500 text-sm mb-6">
          Your payment was successful and your booking is confirmed.
        </p>

        <div className="bg-gray-50 rounded-lg border border-gray-200 p-4 mb-6 text-left space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600">Booking Reference</span>
            <span className="font-mono font-medium">{bookingId || '—'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Status</span>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
              Confirmed
            </span>
          </div>
          <div className="border-t pt-2 mt-2">
            <p className="text-xs text-gray-500">
              Please save your booking reference. You will need it for check-in.
            </p>
          </div>
        </div>

        <div className="mb-6">
          <p className="text-xs text-gray-500 mb-2">Booking ID (QR placeholder)</p>
          <div className="inline-block p-3 bg-white border border-gray-200 rounded-lg">
            <div className="font-mono text-lg font-bold text-gray-900 tracking-widest">
              {bookingId ? bookingId.slice(0, 8).toUpperCase() : '—'}
            </div>
          </div>
        </div>

        <a
          href="/book"
          className="inline-block w-full py-2.5 px-4 rounded-lg bg-brand-600 text-white font-medium hover:bg-brand-700 text-sm"
        >
          Book Another Stay {countdown > 0 ? `(${countdown})` : ''}
        </a>

        <div className="mt-4">
          <a href="/guest/login" className="text-sm text-brand-600 hover:text-brand-700 hover:underline">
            Go to Guest Dashboard
          </a>
        </div>
      </div>
    </div>
  )
}
