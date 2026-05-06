import { useNavigate } from 'react-router-dom'
import { useGuestAuth } from '@/hooks/useGuestAuth'

export default function GuestDashboard() {
  const { user, logout } = useGuestAuth()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-teal-50">
      <div className="max-w-3xl mx-auto px-4 py-8">
        <div className="bg-white rounded-2xl shadow-lg p-6 sm:p-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
            <div>
              <h1 className="text-2xl font-bold text-teal-800">
                Welcome{user?.name ? `, ${user.name}` : ''}
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

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-4 bg-gray-50 rounded-xl border border-gray-100">
              <h2 className="text-lg font-semibold text-gray-800">My Bookings</h2>
              <p className="text-sm text-gray-500 mt-1">You have no upcoming bookings.</p>
              <button
                onClick={() => navigate('/guest/bookings')}
                className="mt-3 text-sm text-teal-600 font-medium hover:text-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 rounded"
              >
                View all bookings
              </button>
            </div>

            <div className="p-4 bg-gray-50 rounded-xl border border-gray-100">
              <h2 className="text-lg font-semibold text-gray-800">Profile</h2>
              <p className="text-sm text-gray-500 mt-1">Manage your personal details.</p>
              <button
                onClick={() => navigate('/guest/profile')}
                className="mt-3 text-sm text-teal-600 font-medium hover:text-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 rounded"
              >
                Edit profile
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
