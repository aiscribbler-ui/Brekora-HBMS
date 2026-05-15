import { useNavigate } from 'react-router-dom'
import {
  InboxArrowDownIcon,
  CreditCardIcon,
  BanknotesIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline'

export interface OpenTasksProps {
  otaQueueReview: number
  paymentFailures: number
  pendingRefunds: number
}

export default function OpenTasks({ otaQueueReview, paymentFailures, pendingRefunds }: OpenTasksProps) {
  const navigate = useNavigate()
  const total = otaQueueReview + paymentFailures + pendingRefunds

  const tasks = [
    {
      label: 'OTA Queue Review',
      count: otaQueueReview,
      icon: InboxArrowDownIcon,
      onClick: () => navigate('/ota/queue'),
    },
    {
      label: 'Payment Failures',
      count: paymentFailures,
      icon: CreditCardIcon,
      onClick: undefined,
    },
    {
      label: 'Pending Refunds',
      count: pendingRefunds,
      icon: BanknotesIcon,
      onClick: undefined,
    },
  ]

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-5 hover:shadow-md transition-shadow">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Open Tasks</h2>
      <div className="space-y-2">
        {tasks.map((task) => {
          const Icon = task.icon
          const clickable = !!task.onClick
          const Wrapper = clickable ? 'button' : 'div'
          return (
            <Wrapper
              key={task.label}
              {...(clickable ? { onClick: task.onClick } : {})}
              className={`w-full flex items-center justify-between rounded-lg px-3 py-2 text-left transition-colors ${
                clickable
                  ? 'hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2'
                  : ''
              }`}
            >
              <div className="flex items-center gap-2.5">
                <Icon className="h-4 w-4 text-gray-500 dark:text-gray-400" aria-hidden="true" />
                <span className="text-sm text-gray-700 dark:text-gray-300">{task.label}</span>
              </div>
              <span
                className={`inline-flex items-center justify-center px-2.5 py-0.5 rounded-full text-sm font-bold ${
                  task.count > 0 ? 'bg-red-100 dark:bg-red-900/20 text-red-800 dark:text-red-400' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                }`}
              >
                {task.count}
              </span>
            </Wrapper>
          )
        })}
      </div>
      {total > 0 && (
        <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg text-sm text-red-700 dark:text-red-400 flex items-center gap-2 animate-pulse">
          <ExclamationTriangleIcon className="h-4 w-4 shrink-0" aria-hidden="true" />
          {total} task{total !== 1 ? 's' : ''} require attention
        </div>
      )}
    </div>
  )
}
