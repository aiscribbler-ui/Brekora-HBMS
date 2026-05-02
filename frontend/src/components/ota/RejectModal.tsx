import { useState } from 'react'
import { Dialog, DialogPanel, DialogTitle, Transition, TransitionChild } from '@headlessui/react'
import { ExclamationTriangleIcon, XCircleIcon } from '@heroicons/react/24/outline'
import { isAxiosError } from '@/lib/api'
import { rejectOtaQueueItem, type ParsedBooking } from '@/services/otaApi'

interface RejectModalProps {
  isOpen: boolean
  onClose: () => void
  booking: ParsedBooking | null
  onSuccess: (updated: ParsedBooking) => void
  onError: (message: string) => void
}

export default function RejectModal({ isOpen, onClose, booking, onSuccess, onError }: RejectModalProps) {
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(false)

  const handleReject = async () => {
    if (!booking || !reason.trim()) return
    setLoading(true)
    try {
      const updated = await rejectOtaQueueItem(booking.id, { rejection_reason: reason.trim() })
      onSuccess(updated)
      setReason('')
    } catch (err) {
      if (isAxiosError(err) && err.response?.data?.detail) {
        onError(err.response.data.detail)
      } else {
        onError('Failed to reject booking.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    if (loading) return
    setReason('')
    onClose()
  }

  if (!booking) return null

  return (
    <Transition show={isOpen} as="div">
      <Dialog onClose={handleClose} className="relative z-50">
        <TransitionChild
          enter="ease-out duration-200"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-150"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/50" aria-hidden="true" />
        </TransitionChild>
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <TransitionChild
            enter="ease-out duration-200"
            enterFrom="opacity-0 scale-95"
            enterTo="opacity-100 scale-100"
            leave="ease-in duration-150"
            leaveFrom="opacity-100 scale-100"
            leaveTo="opacity-0 scale-95"
          >
            <DialogPanel className="w-full max-w-md bg-white rounded-lg shadow-xl p-6">
              <div className="flex items-center gap-3 mb-4">
                <XCircleIcon className="h-6 w-6 text-red-600" />
                <DialogTitle className="text-lg font-semibold text-gray-900">Reject Booking</DialogTitle>
              </div>

              <div className="bg-gray-50 rounded-md p-3 mb-4 text-sm space-y-1">
                <p className="text-gray-500">
                  Guest: <span className="font-medium text-gray-900">{booking.guest_name || '—'}</span>
                </p>
                <p className="text-gray-500">
                  Dates:{' '}
                  <span className="font-medium text-gray-900">
                    {booking.check_in && booking.check_out
                      ? `${booking.check_in} → ${booking.check_out}`
                      : '—'}
                  </span>
                </p>
              </div>

              <div className="mb-4">
                <label htmlFor="reject-reason" className="block text-sm font-medium text-gray-700 mb-1">
                  Rejection Reason <span className="text-red-500">*</span>
                </label>
                <textarea
                  id="reject-reason"
                  rows={3}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="e.g. Duplicate booking, Invalid dates, No availability..."
                  className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
                {!reason.trim() && (
                  <p className="mt-1 text-xs text-gray-500">A reason is required to reject this booking.</p>
                )}
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  onClick={handleClose}
                  disabled={loading}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleReject}
                  disabled={loading || !reason.trim()}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-50 transition-colors"
                >
                  {loading ? 'Rejecting...' : 'Reject'}
                </button>
              </div>
            </DialogPanel>
          </TransitionChild>
        </div>
      </Dialog>
    </Transition>
  )
}
