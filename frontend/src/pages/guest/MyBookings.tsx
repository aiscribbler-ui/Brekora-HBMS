import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchGuestBookings, type GuestBooking } from '@/services/guestApi'
import { isAxiosError } from '@/lib/api'

export default function MyBookings() {
  const navigate = useNavigate()
  const [bookings, setBookings] = useState<GuestBooking[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetchGuestBookings()
      .then((data) => {
        if (!cancelled) setBookings(data)
      })
      .catch((err) => {
        if (!cancelled) {
          if (isAxiosError(err) && err.response?.status === 401) {
            setError('Please log in to view your bookings.')
          } else {
            setError('Failed to load bookings.')
          }
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  const statusBadge = (status: string) => {
    switch (status) {
      case 'confirmed':
        return 'bg-green-100 text-green-800'
      case 'pending_payment':
        return 'bg-yellow-100 text-yellow-800'
      case 'payment_failed':
        return 'bg-red-100 text-red-800'
      case 'cancelled':
        return 'bg-gray-100 text-gray-800'
      case 'completed':
        return 'bg-blue-100 text-blue-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="min-h-screen bg-teal-50">
      <div className="max-w-3xl mx-auto px-4 py-8">
        <div className="bg-white rounded-2xl shadow-lg p-6 sm:p-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold text-teal-800">My Bookings</h1>
              <p className="text-sm text-teal-700 mt-1">View your reservation history</p>
            </div>
            <button
              onClick={() => navigate('/guest')}
              className="text-sm text-teal-700 hover:text-teal-700 font-medium"
            >
              Back to Dashboard
            </button>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm" role="alert">
              {error}
            </div>
          )}

          {loading ? (
            <div className="space-y-4">
              {[1, 2].map((i) => (
                <div key={i} className="h-24 bg-gray-100 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : bookings.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500 text-sm">You have no bookings yet.</p>
              <button
                onClick={() => navigate('/book')}
                className="mt-4 text-sm text-teal-700 font-medium hover:text-teal-700"
              >
                Book a stay
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {bookings.map((booking) => (
                <div
                  key={booking.id}
                  className="border border-gray-200 rounded-xl p-4 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <div>
                      <p className="font-semibold text-gray-900">Property {booking.property_id.slice(0, 8)}</p>
                      <p className="text-sm text-gray-500 mt-1">
                        {new Date(booking.check_in).toLocaleDateString()} — {new Date(booking.check_out).toLocaleDateString()}
                      </p>
                      <p className="text-sm text-gray-700 mt-1 font-medium">
                        {booking.currency} {Number(booking.total_amount).toFixed(2)}
                      </p>
                    </div>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${statusBadge(booking.status)}`}>
                      {booking.status.replace('_', ' ')}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
