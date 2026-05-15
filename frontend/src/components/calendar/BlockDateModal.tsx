import { useState } from 'react'
import type { CalendarRoomType } from '@/services/calendarApi'

interface BlockDateModalProps {
  isOpen: boolean
  onClose: () => void
  onBlock: (reason: string, startDate: string, endDate: string, roomTypeIds: string[]) => void
  roomTypes: CalendarRoomType[]
  defaultStartDate?: string
}

export default function BlockDateModal({
  isOpen,
  onClose,
  onBlock,
  roomTypes,
  defaultStartDate,
}: BlockDateModalProps) {
  const [reason, setReason] = useState('')
  const [startDate, setStartDate] = useState(defaultStartDate || '')
  const [endDate, setEndDate] = useState(defaultStartDate || '')
  const [selectedRoomTypes, setSelectedRoomTypes] = useState<string[]>([])

  if (!isOpen) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!reason || !startDate || !endDate || selectedRoomTypes.length === 0) return
    onBlock(reason, startDate, endDate, selectedRoomTypes)
    setReason('')
    setStartDate('')
    setEndDate('')
    setSelectedRoomTypes([])
    onClose()
  }

  const toggleRoomType = (id: string, checked: boolean) => {
    if (checked) {
      setSelectedRoomTypes((prev) => [...prev, id])
    } else {
      setSelectedRoomTypes((prev) => prev.filter((rtId) => rtId !== id))
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      data-testid="block-date-modal"
    >
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 max-w-md w-full"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Block Dates</h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="block-reason" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Reason <span className="text-red-500 dark:text-red-400">*</span>
            </label>
            <input
              id="block-reason"
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              required
              className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="block-start" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Start Date <span className="text-red-500 dark:text-red-400">*</span>
              </label>
              <input
                id="block-start"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                required
                className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>
            <div>
              <label htmlFor="block-end" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                End Date <span className="text-red-500 dark:text-red-400">*</span>
              </label>
              <input
                id="block-end"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                required
                className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>
          </div>
          <div>
            <span className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Room Types <span className="text-red-500 dark:text-red-400">*</span>
            </span>
            <div className="space-y-2 max-h-40 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded-md p-2">
              {roomTypes.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">No room types available.</p>
              ) : (
                roomTypes.map((rt) => (
                  <label key={rt.id} className="flex items-center gap-2 text-sm cursor-pointer dark:text-gray-300">
                    <input
                      type="checkbox"
                      value={rt.id}
                      checked={selectedRoomTypes.includes(rt.id)}
                      onChange={(e) => toggleRoomType(rt.id, e.target.checked)}
                      className="rounded border-gray-300 dark:border-gray-600 text-brand-600 focus:ring-brand-500"
                    />
                    {rt.name}
                  </label>
                ))
              )}
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded hover:bg-brand-700 transition-colors"
            >
              Block
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
