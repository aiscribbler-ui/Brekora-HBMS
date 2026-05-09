import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchGuestProfile, updateGuestProfile, type GuestProfile } from '@/services/guestApi'
import { isAxiosError } from '@/lib/api'

export default function GuestProfilePage() {
  const navigate = useNavigate()
  const [profile, setProfile] = useState<GuestProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetchGuestProfile()
      .then((data) => {
        if (!cancelled) setProfile(data)
      })
      .catch((err) => {
        if (!cancelled) {
          if (isAxiosError(err) && err.response?.status === 401) {
            setError('Please log in to view your profile.')
          } else {
            setError('Failed to load profile.')
          }
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  const handleChange = (field: keyof GuestProfile, value: string) => {
    setProfile((prev) => (prev ? { ...prev, [field]: value } : prev))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!profile) return
    setError(null)
    setSuccess(null)
    setSaving(true)
    try {
      const updated = await updateGuestProfile({
        first_name: profile.first_name,
        last_name: profile.last_name,
        phone: profile.phone,
      })
      setProfile(updated)
      setSuccess('Profile updated successfully.')
    } catch (err) {
      if (isAxiosError(err) && err.response?.data?.detail) {
        setError(err.response.data.detail)
      } else {
        setError('Failed to update profile.')
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen bg-teal-50">
      <div className="max-w-2xl mx-auto px-4 py-8">
        <div className="bg-white rounded-2xl shadow-lg p-6 sm:p-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold text-teal-800">My Profile</h1>
              <p className="text-sm text-teal-700 mt-1">Manage your personal details</p>
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
          {success && (
            <div className="mb-4 p-3 bg-green-50 text-green-800 rounded-lg border border-green-200 text-sm" role="status">
              {success}
            </div>
          )}

          {loading ? (
            <div className="space-y-4">
              <div className="h-8 bg-gray-100 rounded w-1/2 animate-pulse" />
              <div className="h-24 bg-gray-100 rounded animate-pulse" />
            </div>
          ) : profile ? (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="first_name" className="block text-sm font-medium text-gray-700">First Name</label>
                  <input
                    id="first_name"
                    type="text"
                    value={profile.first_name ?? ''}
                    onChange={(e) => handleChange('first_name', e.target.value)}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 shadow-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
                  />
                </div>
                <div>
                  <label htmlFor="last_name" className="block text-sm font-medium text-gray-700">Last Name</label>
                  <input
                    id="last_name"
                    type="text"
                    value={profile.last_name ?? ''}
                    onChange={(e) => handleChange('last_name', e.target.value)}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 shadow-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700">Email</label>
                <input
                  id="email"
                  type="email"
                  value={profile.email}
                  disabled
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 shadow-sm bg-gray-50 text-gray-500 cursor-not-allowed"
                />
                <p className="text-xs text-gray-400 mt-1">Email cannot be changed.</p>
              </div>

              <div>
                <label htmlFor="phone" className="block text-sm font-medium text-gray-700">Phone</label>
                <input
                  id="phone"
                  type="tel"
                  value={profile.phone ?? ''}
                  onChange={(e) => handleChange('phone', e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 shadow-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
                />
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 bg-teal-700 text-white font-medium rounded-lg hover:bg-teal-700 disabled:opacity-50 transition-colors focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2"
                >
                  {saving ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          ) : (
            <p className="text-sm text-gray-500">Unable to load profile.</p>
          )}
        </div>
      </div>
    </div>
  )
}
