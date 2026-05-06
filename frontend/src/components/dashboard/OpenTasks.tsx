import { useNavigate } from 'react-router-dom'
import { Inbox, AlertTriangle, RefreshCcw, AlertOctagon, ChevronRight } from 'lucide-react'

export interface OpenTasksProps {
  otaQueueReview: number
  paymentFailures: number
  pendingRefunds: number
}

export default function OpenTasks({ otaQueueReview, paymentFailures, pendingRefunds }: OpenTasksProps) {
  const navigate = useNavigate()
  const total = otaQueueReview + paymentFailures + pendingRefunds

  const items = [
    {
      label: 'OTA Queue Review',
      count: otaQueueReview,
      icon: Inbox,
      onClick: () => navigate('/ota/queue'),
      ariaLabel: `OTA Queue Review, ${otaQueueReview} pending`,
      clickable: true,
    },
    {
      label: 'Payment Failures',
      count: paymentFailures,
      icon: AlertTriangle,
      onClick: undefined,
      ariaLabel: `Payment Failures, ${paymentFailures} pending`,
      clickable: false,
    },
    {
      label: 'Pending Refunds',
      count: pendingRefunds,
      icon: RefreshCcw,
      onClick: undefined,
      ariaLabel: `Pending Refunds, ${pendingRefunds} pending`,
      clickable: false,
    },
  ]

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 h-full">
      <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <span className="w-1.5 h-5 bg-gradient-to-b from-brand-500 to-brand-700 rounded-full" aria-hidden="true" />
        Open Tasks
      </h3>
      <div className="space-y-2">
        {items.map(({ label, count, icon: Icon, onClick, ariaLabel, clickable }) => {
          const isActive = count > 0
          const content = (
            <>
              <span className="flex items-center gap-2.5">
                <span
                  className={`inline-flex items-center justify-center w-8 h-8 rounded-lg ${
                    isActive ? 'bg-red-50 text-red-600' : 'bg-gray-100 text-gray-400'
                  }`}
                  aria-hidden="true"
                >
                  <Icon className="w-4 h-4" />
                </span>
                <span className="text-sm text-gray-700">{label}</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span
                  className={`inline-flex items-center justify-center min-w-[1.75rem] h-7 px-2 rounded-full text-sm font-bold ${
                    isActive ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-500'
                  }`}
                >
                  {count}
                </span>
                {clickable && <ChevronRight className="w-4 h-4 text-gray-300" aria-hidden="true" />}
              </span>
            </>
          )

          if (clickable && onClick) {
            return (
              <button
                key={label}
                onClick={onClick}
                className="w-full flex items-center justify-between hover:bg-gray-50 rounded-lg px-2 py-1.5 transition-colors text-left focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
                aria-label={ariaLabel}
              >
                {content}
              </button>
            )
          }

          return (
            <div
              key={label}
              className="flex items-center justify-between px-2 py-1.5 rounded-lg"
            >
              {content}
            </div>
          )
        })}
      </div>
      {total > 0 && (
        <div
          className="mt-4 flex items-center gap-2 p-2.5 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 animate-pulse-soft"
          role="alert"
        >
          <AlertOctagon className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
          <span className="font-medium">
            {total} task{total !== 1 ? 's' : ''} require attention
          </span>
        </div>
      )}
    </div>
  )
}
