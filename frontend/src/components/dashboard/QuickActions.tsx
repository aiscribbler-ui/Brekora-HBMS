import { useNavigate } from 'react-router-dom'
import {
  PlusIcon,
  CalendarIcon,
  ChatBubbleLeftRightIcon,
  InboxArrowDownIcon,
  LinkIcon,
} from '@heroicons/react/24/outline'

export default function QuickActions() {
  const navigate = useNavigate()

  const actions = [
    {
      label: 'Create Booking',
      icon: PlusIcon,
      onClick: () => navigate('/bookings/manual'),
      testId: 'action-create-booking',
    },
    {
      label: 'Block Dates',
      icon: CalendarIcon,
      onClick: () => navigate('/calendar'),
      testId: 'action-block-dates',
    },
    {
      label: 'Message Guest',
      icon: ChatBubbleLeftRightIcon,
      onClick: () => navigate('/messages'),
      testId: 'action-message-guest',
    },
    {
      label: 'Review OTA Queue',
      icon: InboxArrowDownIcon,
      onClick: () => navigate('/ota/queue'),
      testId: 'action-ota-queue',
    },
    {
      label: 'Edit OTA Mapping',
      icon: LinkIcon,
      onClick: () => navigate('/ota/mappings'),
      testId: 'action-ota-mapping',
    },
  ]

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 hover:shadow-md transition-shadow">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
      <div className="grid grid-cols-2 gap-3">
        {actions.map((action) => {
          const Icon = action.icon
          return (
            <button
              key={action.testId}
              onClick={action.onClick}
              className="flex flex-col items-center justify-center gap-2 p-4 rounded-xl border border-gray-200 hover:bg-brand-50 hover:border-brand-300 hover:-translate-y-0.5 transition-all focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
              data-testid={action.testId}
              aria-label={action.label}
            >
              <Icon className="h-6 w-6 text-brand-600" aria-hidden="true" />
              <span className="text-sm font-medium text-gray-700">{action.label}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
