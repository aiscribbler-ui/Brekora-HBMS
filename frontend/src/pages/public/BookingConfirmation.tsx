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
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 p-8 text-center">
        <div className="mx-auto h-12 w-12 bg-success-light rounded-full flex items-center justify-center mb-4">
          <svg className="h-6 w-6 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>

        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2 font-display">Booking Confirmed!</h1>
        <p className="text-gray-500 dark:text-gray-400 text-sm mb-6">
          Your payment was successful and your booking is confirmed.
        </p>

        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 mb-6 text-left space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600 dark:text-gray-300">Booking Reference</span>
            <span className="font-mono font-medium">{bookingId || '—'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600 dark:text-gray-300">Status</span>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-success-light text-success-dark">
              Confirmed
            </span>
          </div>
          <div className="border-t dark:border-gray-700 pt-2 mt-2">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Please save your booking reference. You will need it for check-in.
            </p>
          </div>
        </div>

        <div className="mb-6">
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Booking ID (QR placeholder)</p>
          <div className="inline-block p-3 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-700 rounded-lg">
            <div className="font-mono text-lg font-bold text-gray-900 dark:text-gray-100 tracking-widest">
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
