import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useGuestAuth } from '@/hooks/useGuestAuth'
import {
  fetchGuestBookings,
  fetchGuestProfile,
  type GuestBooking,
  type GuestProfile,
} from '@/services/guestApi'

function formatDate(value: string): string {
  try {
    return new Date(value).toLocaleDateString(undefined, {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    })
  } catch {
    return value
  }
}

function statusBadge(status: string): string {
  const s = status.toLowerCase()
  if (s === 'confirmed' || s === 'checked_in') return 'bg-emerald-100 text-emerald-700'
  if (s === 'cancelled') return 'bg-red-100 text-red-700'
  if (s === 'pending_payment' || s === 'payment_failed') return 'bg-amber-100 text-amber-700'
  return 'bg-gray-100 text-gray-700'
}

export default function GuestDashboard() {
  const { user, logout } = useGuestAuth()
  const navigate = useNavigate()
  const [profile, setProfile] = useState<GuestProfile | null>(null)
  const [bookings, setBookings] = useState<GuestBooking[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    Promise.all([
      fetchGuestProfile().catch(() => null),
      fetchGuestBookings().catch(() => []),
    ])
      .then(([p, b]) => {
        if (cancelled) return
        setProfile(p)
        setBookings(b)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const greetingName =
    profile?.first_name || user?.name || profile?.email?.split('@')[0] || ''

  return (
    <div className="min-h-screen bg-teal-50">
      <div className="max-w-3xl mx-auto px-4 py-8">
        <div className="bg-white rounded-2xl shadow-lg p-6 sm:p-8 mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-teal-800">
                Welcome{greetingName ? `, ${greetingName}` : ''}
              </h1>
              <p className="text-sm text-teal-600 mt-1">Your guest portal</p>
            </div>
            <button
              onClick={logout}
              className="self-start sm:self-auto py-2 px-4 bg-red-50 text-red-700 font-medium rounded-lg border border-red-200 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 transition-colors"
            >
              Logout
            </button>
          </div>
        </div>

        <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">My Bookings</h2>
          {loading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : bookings.length === 0 ? (
            <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 px-4 py-8 text-center">
              <p className="text-sm text-gray-500">You have no bookings yet.</p>
              <button
                type="button"
                onClick={() => navigate('/book')}
                className="mt-3 text-sm text-teal-600 font-medium hover:text-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 rounded"
              >
                Find a stay →
              </button>
            </div>
          ) : (
            <ul className="divide-y divide-gray-100">
              {bookings.map((b) => (
                <li key={b.id} className="py-3 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900">
                      Booking {b.id.slice(0, 8)}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {formatDate(b.check_in)} → {formatDate(b.check_out)}
                    </p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusBadge(b.status)}`}
                    >
                      {b.status.replace(/_/g, ' ')}
                    </span>
                    <p className="text-xs text-gray-500 mt-1 tabular-nums">
                      {b.currency} {b.total_amount.toLocaleString()}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Profile</h2>
          {loading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : profile ? (
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-xs text-gray-500">Name</dt>
                <dd className="font-medium text-gray-900">
                  {[profile.first_name, profile.last_name].filter(Boolean).join(' ') || '—'}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-gray-500">Email</dt>
                <dd className="font-medium text-gray-900 break-all">{profile.email}</dd>
              </div>
              <div>
                <dt className="text-xs text-gray-500">Phone</dt>
                <dd className="font-medium text-gray-900">{profile.phone || '—'}</dd>
              </div>
            </dl>
          ) : (
            <p className="text-sm text-gray-500">Profile unavailable.</p>
          )}
          <div className="mt-4">
            <button
              type="button"
              onClick={() => navigate('/guest/profile')}
              className="text-sm text-teal-600 font-medium hover:text-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 rounded"
            >
              Edit profile
            </button>
          </div>
        </section>
      </div>
    </div>
  )
}
