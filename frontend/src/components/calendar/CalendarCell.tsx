import { useState } from 'react'
import type { CalendarRoomType, CalendarAvailability } from '@/services/calendarApi'

interface CalendarCellProps {
  dateStr: string
  roomType: CalendarRoomType
  availability?: CalendarAvailability
}

export default function CalendarCell({ dateStr, roomType, availability }: CalendarCellProps) {
  const [showModal, setShowModal] = useState(false)

  const available = availability?.available_count ?? roomType.count
  const total = availability?.total_count ?? roomType.count
  const booked = availability?.booked_count ?? 0
  const held = availability?.held_count ?? 0

  const ratio = total > 0 ? available / total : 0

  let bgClass = 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300'
  let statusLabel = 'Unknown'
  if (total === 0) {
    bgClass = 'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
    statusLabel = 'No inventory'
  } else if (ratio === 0) {
    bgClass = 'bg-red-100 dark:bg-red-900/20 text-red-800 dark:text-red-400'
    statusLabel = 'Fully booked'
  } else if (ratio <= 0.5) {
    bgClass = 'bg-warning-light text-warning-dark'
    statusLabel = 'Low availability'
  } else {
    bgClass = 'bg-success-light text-success-dark'
    statusLabel = 'Available'
  }

  const tooltip = `Available: ${available}\nBooked: ${booked}\nHeld: ${held}\nTotal: ${total}`
  const ariaLabel = `${roomType.name} on ${dateStr}: ${statusLabel}. Available ${available} of ${total}. Booked ${booked}, held ${held}.`

  return (
    <>
      <button
        type="button"
        role="gridcell"
        aria-label={ariaLabel}
        className={`min-w-[3rem] h-10 w-full flex items-center justify-center text-xs font-medium rounded transition-colors hover:opacity-80 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-1 ${bgClass}`}
        title={tooltip}
        onClick={() => setShowModal(true)}
        data-testid={`cell-${roomType.id}-${dateStr}`}
      >
        {available}/{total}
      </button>

      {showModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={() => setShowModal(false)}
          role="dialog"
          aria-modal="true"
          data-testid={`booking-modal-${roomType.id}-${dateStr}`}
        >
          <div
            className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 max-w-sm w-full"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
              {roomType.name} — {dateStr}
            </h3>
            <div className="space-y-1 text-sm text-gray-600 dark:text-gray-300">
              <p>Available: {available}</p>
              <p>Booked: {booked}</p>
              <p>Held: {held}</p>
              <p>Total: {total}</p>
            </div>
            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded hover:bg-brand-700 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
