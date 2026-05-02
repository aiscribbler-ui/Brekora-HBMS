import { useNavigate } from 'react-router-dom'

export interface OpenTasksProps {
  otaQueueReview: number
  paymentFailures: number
  pendingRefunds: number
}

export default function OpenTasks({ otaQueueReview, paymentFailures, pendingRefunds }: OpenTasksProps) {
  const navigate = useNavigate()
  const total = otaQueueReview + paymentFailures + pendingRefunds

  return (
    <div className="bg-white rounded-lg shadow p-5">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Open Tasks</h3>
      <div className="space-y-3">
        <button
          onClick={() => navigate('/ota/queue')}
          className="w-full flex items-center justify-between hover:bg-gray-50 rounded px-2 py-1 -mx-2 -my-1 transition-colors text-left focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
          aria-label={`OTA Queue Review, ${otaQueueReview} pending`}
        >
          <span className="text-sm text-gray-700">OTA Queue Review</span>
          <span
            className={`inline-flex items-center justify-center px-2.5 py-0.5 rounded-full text-sm font-bold ${
              otaQueueReview > 0 ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-600'
            }`}
          >
            {otaQueueReview}
          </span>
        </button>
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-700">Payment Failures</span>
          <span
            className={`inline-flex items-center justify-center px-2.5 py-0.5 rounded-full text-sm font-bold ${
              paymentFailures > 0 ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-600'
            }`}
          >
            {paymentFailures}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-700">Pending Refunds</span>
          <span
            className={`inline-flex items-center justify-center px-2.5 py-0.5 rounded-full text-sm font-bold ${
              pendingRefunds > 0 ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-600'
            }`}
          >
            {pendingRefunds}
          </span>
        </div>
      </div>
      {total > 0 && (
        <div className="mt-4 p-2 bg-red-50 rounded text-sm text-red-700">
          {total} task{total !== 1 ? 's' : ''} require attention
        </div>
      )}
    </div>
  )
}
