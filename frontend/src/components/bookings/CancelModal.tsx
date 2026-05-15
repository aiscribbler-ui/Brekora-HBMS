import { useState } from 'react'
import type { Booking } from '@/services/bookingApi'
import RefundCalculator from './RefundCalculator'

interface CancelModalProps {
  booking: Booking | null
  isOpen: boolean
  onClose: () => void
  onConfirm: (reason: string) => Promise<void>
}

export default function CancelModal({ booking, isOpen, onClose, onConfirm }: CancelModalProps) {
  const [reason, setReason] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (!isOpen || !booking) return null

  const daysUntilCheckIn = Math.ceil(
    (new Date(booking.check_in).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24),
  )

  const handleConfirm = async () => {
    if (!reason.trim()) return
    setIsSubmitting(true)
    try {
      await onConfirm(reason.trim())
      setReason('')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-lg w-full">
        <div className="px-6 py-4 border-b dark:border-gray-700">
          <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">Cancel Booking</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Reference: {booking.id}
          </p>
        </div>

        <div className="px-6 py-4 space-y-4">
          <RefundCalculator
            totalAmount={booking.total_amount}
            policy={booking.cancellation_policy_snapshot as Parameters<typeof RefundCalculator>[0]['policy']}
            daysUntilCheckIn={Math.max(0, daysUntilCheckIn)}
          />

          <div>
            <label htmlFor="cancellationReason" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Reason for cancellation *
            </label>
            <textarea
              id="cancellationReason"
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 text-sm"
              placeholder="Enter reason..."
            />
          </div>
        </div>

        <div className="px-6 py-4 border-t dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="px-4 py-2 rounded-md border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50 font-medium text-sm transition-colors"
          >
            Close
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={!reason.trim() || isSubmitting}
            className="px-4 py-2 rounded-md bg-red-600 text-white font-medium hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
          >
            {isSubmitting ? 'Cancelling...' : 'Confirm Cancellation'}
          </button>
        </div>
      </div>
    </div>
  )
}
