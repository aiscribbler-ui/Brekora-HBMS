import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { MapPin } from 'lucide-react'
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
  if (s === 'confirmed' || s === 'checked_in') return 'bg-success-light text-success'
  if (s === 'cancelled') return 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
  if (s === 'pending_payment' || s === 'payment_failed') return 'bg-warning-light dark:bg-warning-dark/20 text-warning-dark dark:text-warning-light'
  return 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
}

export default function GuestDashboard() {
  const { user, logout } = useGuestAuth()
  const navigate = useNavigate()

  const [bookings, setBookings] = useState<GuestBooking[]>([])
  const [profile, setProfile] = useState<GuestProfile | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const [b, p] = await Promise.all([fetchGuestBookings(), fetchGuestProfile()])
        if (!cancelled) {
          setBookings(b)
          setProfile(p)
        }
      } catch {
        // ignore
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  const greetingName = user?.name || [profile?.first_name, profile?.last_name].filter(Boolean).join(' ') || profile?.email

  return (
    <div className="min-h-screen bg-brand-50 dark:bg-gray-900">
      <div className="max-w-3xl mx-auto px-4 py-8">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 sm:p-8 mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-brand-700 dark:text-brand-300 font-display">
                Welcome{greetingName ? `, ${greetingName}` : ''}
              </h1>
              <p className="text-sm text-brand-700 dark:text-brand-400 mt-1">Your guest portal</p>
            </div>
            <button
              onClick={logout}
              className="self-start sm:self-auto py-2 px-4 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 font-medium rounded-lg border border-red-200 dark:border-red-800 hover:bg-red-100 dark:hover:bg-red-900/30 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 transition-colors"
            >
              Logout
            </button>
          </div>
        </div>

        <section className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 sm:p-8 mb-6">
          <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">My Bookings</h2>
          {loading ? (
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">Loading…</p>
          ) : bookings.length === 0 ? (
            <div className="mt-2">
              <p className="text-sm text-gray-500 dark:text-gray-400">You have no upcoming bookings.</p>
              <button
                onClick={() => navigate('/guest/bookings')}
                className="mt-3 text-sm text-brand-600 dark:text-brand-400 font-medium hover:text-brand-700 dark:hover:text-brand-300 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 rounded"
              >
                Find a stay →
              </button>
            </div>
          ) : (
            <ul className="divide-y divide-gray-100 dark:divide-gray-700 mt-2">
              {bookings.map((b) => (
                <li key={b.id} className="py-3 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100 flex items-center gap-1.5">
                      <MapPin className="w-3.5 h-3.5 text-gray-400 dark:text-gray-500" />
                      Booking {b.id.slice(0, 8)}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      {formatDate(b.check_in)} → {formatDate(b.check_out)}
                    </p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusBadge(
                        b.status,
                      )}`}
                    >
                      {b.status.replace(/_/g, ' ')}
                    </span>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 tabular-nums">
                      {b.currency} {b.total_amount.toLocaleString()}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 sm:p-8">
          <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">Profile</h2>
          {loading ? (
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">Loading…</p>
          ) : !profile ? (
            <div className="mt-2">
              <p className="text-sm text-gray-500 dark:text-gray-400">Manage your personal details.</p>
              <button
                onClick={() => navigate('/guest/profile')}
                className="mt-3 text-sm text-brand-600 dark:text-brand-400 font-medium hover:text-brand-700 dark:hover:text-brand-300 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 rounded"
              >
                Edit profile
              </button>
            </div>
          ) : (
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm mt-3">
              <div>
                <dt className="text-xs text-gray-500 dark:text-gray-400">Name</dt>
                <dd className="font-medium text-gray-900 dark:text-gray-100">
                  {[profile.first_name, profile.last_name].filter(Boolean).join(' ') || '—'}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-gray-500 dark:text-gray-400">Email</dt>
                <dd className="font-medium text-gray-900 dark:text-gray-100 break-all">{profile.email}</dd>
              </div>
              <div>
                <dt className="text-xs text-gray-500 dark:text-gray-400">Phone</dt>
                <dd className="font-medium text-gray-900 dark:text-gray-100">{profile.phone || '—'}</dd>
              </div>
            </dl>
          )}
        </section>
      </div>
    </div>
  )
}
