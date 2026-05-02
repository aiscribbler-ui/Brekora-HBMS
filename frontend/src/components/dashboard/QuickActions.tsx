import { useNavigate } from 'react-router-dom'

export default function QuickActions() {
  const navigate = useNavigate()

  return (
    <div className="bg-white rounded-lg shadow p-5">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
      <div className="grid grid-cols-2 gap-3">
        <button
          onClick={() => navigate('/bookings/new')}
          className="flex flex-col items-center justify-center gap-2 p-4 rounded-lg border border-gray-200 hover:bg-brand-50 hover:border-brand-300 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
          data-testid="action-create-booking"
          aria-label="Create booking"
        >
          <span className="text-2xl" aria-hidden="true">+</span>
          <span className="text-sm font-medium text-gray-700">Create Booking</span>
        </button>
        <button
          onClick={() => {
            // stub: opens block dates modal (D-009)
            alert('Block Dates — coming in D-009')
          }}
          className="flex flex-col items-center justify-center gap-2 p-4 rounded-lg border border-gray-200 hover:bg-brand-50 hover:border-brand-300 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
          data-testid="action-block-dates"
          aria-label="Block dates"
        >
          <span className="text-2xl" aria-hidden="true">📅</span>
          <span className="text-sm font-medium text-gray-700">Block Dates</span>
        </button>
        <button
          onClick={() => {
            // stub: message guest (D-013)
            alert('Message Guest — coming in D-013')
          }}
          className="flex flex-col items-center justify-center gap-2 p-4 rounded-lg border border-gray-200 hover:bg-brand-50 hover:border-brand-300 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
          data-testid="action-message-guest"
          aria-label="Message guest"
        >
          <span className="text-2xl" aria-hidden="true">💬</span>
          <span className="text-sm font-medium text-gray-700">Message Guest</span>
        </button>
        <button
          onClick={() => navigate('/ota/queue')}
          className="flex flex-col items-center justify-center gap-2 p-4 rounded-lg border border-gray-200 hover:bg-brand-50 hover:border-brand-300 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
          data-testid="action-ota-queue"
          aria-label="Review OTA queue"
        >
          <span className="text-2xl" aria-hidden="true">📥</span>
          <span className="text-sm font-medium text-gray-700">Review OTA Queue</span>
        </button>
        <button
          onClick={() => navigate('/ota/mappings')}
          className="flex flex-col items-center justify-center gap-2 p-4 rounded-lg border border-gray-200 hover:bg-brand-50 hover:border-brand-300 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
          data-testid="action-ota-mapping"
          aria-label="Edit OTA mapping"
        >
          <span className="text-2xl" aria-hidden="true">🔗</span>
          <span className="text-sm font-medium text-gray-700">Edit OTA Mapping</span>
        </button>
      </div>
    </div>
  )
}
