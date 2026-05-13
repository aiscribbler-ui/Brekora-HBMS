import { useState, useEffect } from 'react'
import { Dialog, DialogPanel, DialogTitle, Transition, TransitionChild } from '@headlessui/react'
import { ExclamationTriangleIcon, CheckCircleIcon } from '@heroicons/react/24/outline'
import { isAxiosError } from '@/lib/api'
import { confirmOtaQueueItem, type ParsedBooking } from '@/services/otaApi'
import { getRoomTypes, type RoomType } from '@/services/propertyApi'

interface ConfirmModalProps {
  isOpen: boolean
  onClose: () => void
  booking: ParsedBooking | null
  onSuccess: (updated: ParsedBooking) => void
  onError: (message: string) => void
}

export default function ConfirmModal({ isOpen, onClose, booking, onSuccess, onError }: ConfirmModalProps) {
  const [roomTypes, setRoomTypes] = useState<RoomType[]>([])
  const [selectedRoomTypeId, setSelectedRoomTypeId] = useState('')
  const [loading, setLoading] = useState(false)
  const [fetching, setFetching] = useState(false)

  useEffect(() => {
    if (!isOpen || !booking) return
    let cancelled = false
    setFetching(true)
    setSelectedRoomTypeId('')
    getRoomTypes(booking.property_id)
      .then((data) => {
        if (!cancelled) setRoomTypes(data)
      })
      .catch(() => {
        if (!cancelled) setRoomTypes([])
      })
      .finally(() => {
        if (!cancelled) setFetching(false)
      })
    return () => { cancelled = true }
  }, [isOpen, booking])

  const handleConfirm = async () => {
    if (!booking) return
    setLoading(true)
    try {
      const payload = selectedRoomTypeId ? { room_type_id: selectedRoomTypeId } : {}
      const updated = await confirmOtaQueueItem(booking.id, payload)
      onSuccess(updated)
      setSelectedRoomTypeId('')
    } catch (err) {
      if (isAxiosError(err) && err.response?.data?.detail) {
        onError(err.response.data.detail)
      } else {
        onError('Failed to confirm booking.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    if (loading) return
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
            <DialogPanel className="w-full max-w-lg bg-white rounded-lg shadow-xl p-6">
              <div className="flex items-center gap-3 mb-4">
                <CheckCircleIcon className="h-6 w-6 text-success" />
                <DialogTitle className="text-lg font-semibold text-gray-900">Confirm Booking</DialogTitle>
              </div>

              <div className="bg-gray-50 rounded-md p-4 mb-4 space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Guest</span>
                  <span className="font-medium text-gray-900">{booking.guest_name || '—'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Dates</span>
                  <span className="font-medium text-gray-900">
                    {booking.check_in && booking.check_out
                      ? `${booking.check_in} → ${booking.check_out}`
                      : '—'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">OTA Source</span>
                  <span className="font-medium text-gray-900 capitalize">{booking.source_type}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Reference</span>
                  <span className="font-medium text-gray-900">{booking.ota_reference || '—'}</span>
                </div>
              </div>

              <div className="mb-4">
                <label htmlFor="room-type-select" className="block text-sm font-medium text-gray-700 mb-1">
                  Room Type <span className="text-gray-400 font-normal">(optional)</span>
                </label>
                {fetching ? (
                  <div className="h-10 bg-gray-100 rounded animate-pulse" />
                ) : (
                  <select
                    id="room-type-select"
                    value={selectedRoomTypeId}
                    onChange={(e) => setSelectedRoomTypeId(e.target.value)}
                    className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  >
                    <option value="">Auto-detect / Leave blank</option>
                    {roomTypes.map((rt) => (
                      <option key={rt.id} value={rt.id}>
                        {rt.name} (capacity {rt.base_capacity}-{rt.max_capacity})
                      </option>
                    ))}
                  </select>
                )}
                {roomTypes.length === 0 && !fetching && (
                  <p className="mt-1 text-xs text-amber-600">No room types found for this property.</p>
                )}
              </div>

              {booking.confidence_score < 0.8 && (
                <div className="mb-4 p-3 bg-amber-50 rounded border border-amber-200 flex items-start gap-2">
                  <ExclamationTriangleIcon className="h-5 w-5 text-amber-500 shrink-0" />
                  <p className="text-sm text-amber-800">
                    This booking has low confidence ({(booking.confidence_score * 100).toFixed(0)}%). Please verify all details before confirming.
                  </p>
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  onClick={handleClose}
                  disabled={loading}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirm}
                  disabled={loading}
                  className="px-4 py-2 text-sm font-medium text-white bg-success rounded-md hover:bg-success-dark disabled:opacity-50 transition-colors"
                >
                  {loading ? 'Confirming...' : 'Confirm'}
                </button>
              </div>
            </DialogPanel>
          </TransitionChild>
        </div>
      </Dialog>
    </Transition>
  )
}
