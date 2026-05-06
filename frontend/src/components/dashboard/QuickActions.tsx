import { useNavigate } from 'react-router-dom'
import { Plus, CalendarOff, MessageSquare, Inbox, Link2 } from 'lucide-react'

export default function QuickActions() {
  const navigate = useNavigate()

  const actions = [
    {
      label: 'Create Booking',
      icon: Plus,
      onClick: () => navigate('/bookings/manual'),
      testId: 'action-create-booking',
      ariaLabel: 'Create booking',
      gradient: 'from-brand-500 to-brand-700',
    },
    {
      label: 'Block Dates',
      icon: CalendarOff,
      onClick: () => navigate('/calendar'),
      testId: 'action-block-dates',
      ariaLabel: 'Block dates',
      gradient: 'from-amber-500 to-orange-600',
    },
    {
      label: 'Message Guest',
      icon: MessageSquare,
      onClick: () => navigate('/bookings/manual'),
      testId: 'action-message-guest',
      ariaLabel: 'Message guest',
      gradient: 'from-emerald-500 to-teal-600',
    },
    {
      label: 'Review OTA Queue',
      icon: Inbox,
      onClick: () => navigate('/ota/queue'),
      testId: 'action-ota-queue',
      ariaLabel: 'Review OTA queue',
      gradient: 'from-violet-500 to-purple-600',
    },
    {
      label: 'Edit OTA Mapping',
      icon: Link2,
      onClick: () => navigate('/properties'),
      testId: 'action-ota-mapping',
      ariaLabel: 'Edit OTA mapping',
      gradient: 'from-pink-500 to-rose-600',
    },
  ]

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 h-full">
      <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <span className="w-1.5 h-5 bg-gradient-to-b from-brand-500 to-brand-700 rounded-full" aria-hidden="true" />
        Quick Actions
      </h3>
      <div className="grid grid-cols-2 gap-3">
        {actions.map(({ label, icon: Icon, onClick, testId, ariaLabel, gradient }) => (
          <button
            key={testId}
            onClick={onClick}
            className="group relative flex flex-col items-center justify-center gap-2 p-4 rounded-xl border border-gray-200 bg-white hover:border-transparent hover:shadow-md transition-all focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 overflow-hidden"
            data-testid={testId}
            aria-label={ariaLabel}
          >
            <span
              className={`absolute inset-0 bg-gradient-to-br ${gradient} opacity-0 group-hover:opacity-10 transition-opacity`}
              aria-hidden="true"
            />
            <span
              className={`relative inline-flex items-center justify-center w-10 h-10 rounded-lg bg-gradient-to-br ${gradient} text-white shadow-sm group-hover:scale-110 transition-transform`}
              aria-hidden="true"
            >
              <Icon className="w-5 h-5" />
            </span>
            <span className="relative text-sm font-medium text-gray-700 text-center">{label}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
