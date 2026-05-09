import { useState } from 'react'
import {
  format,
  startOfMonth,
  endOfMonth,
  eachDayOfInterval,
  isSameMonth,
  isToday,
} from 'date-fns'
import { useCalendar } from '@/hooks/useCalendar'
import { useAuthStore } from '@/store/authStore'
import CalendarCell from '@/components/calendar/CalendarCell'
import BlockDateModal from '@/components/calendar/BlockDateModal'
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  CalendarIcon,
} from '@heroicons/react/24/outline'

export default function CalendarGrid() {
  const {
    currentMonth,
    selectedPropertyId,
    properties,
    roomTypes,
    availabilityMap,
    isLoading,
    error,
    goToPrevMonth,
    goToNextMonth,
    goToToday,
    setSelectedPropertyId,
    blockDates,
  } = useCalendar()
  const user = useAuthStore((s) => s.user)
  const globalRole = user?.role || ''
  const orgLevelRoles = ['Admin', 'Owner', 'Manager']
  const canBlockDates =
    orgLevelRoles.includes(globalRole) ||
    user?.properties?.some(
      (p) => p.id === selectedPropertyId && p.role_at_property === 'manager',
    ) === true

  const [showBlockModal, setShowBlockModal] = useState(false)

  const monthStart = startOfMonth(currentMonth)
  const monthEnd = endOfMonth(currentMonth)
  const days = eachDayOfInterval({ start: monthStart, end: monthEnd })

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
          Calendar
        </h2>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={goToPrevMonth}
            className="p-2 rounded-md border border-gray-300 hover:bg-gray-100 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
            aria-label="Previous month"
            data-testid="prev-month-btn"
          >
            <ChevronLeftIcon className="h-4 w-4 text-gray-700" />
          </button>
          <button
            type="button"
            onClick={goToToday}
            className="px-3 py-2 rounded-md border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
            data-testid="today-btn"
          >
            Today
          </button>
          <button
            type="button"
            onClick={goToNextMonth}
            className="p-2 rounded-md border border-gray-300 hover:bg-gray-100 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
            aria-label="Next month"
            data-testid="next-month-btn"
          >
            <ChevronRightIcon className="h-4 w-4 text-gray-700" />
          </button>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-2">
          <CalendarIcon className="h-5 w-5 text-gray-500" />
          <span className="text-lg font-semibold text-gray-900" data-testid="month-title">
            {format(currentMonth, 'MMMM yyyy')}
          </span>
        </div>
        <select
          value={selectedPropertyId}
          onChange={(e) => setSelectedPropertyId(e.target.value)}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          data-testid="property-selector"
        >
          <option value="">Select property</option>
          {properties.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <div className="p-3 bg-red-50 text-red-700 rounded border border-red-200" role="alert">
          {error}
        </div>
      )}

      {canBlockDates && (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={() => setShowBlockModal(true)}
            className="px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded hover:bg-brand-700 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
            data-testid="block-dates-btn"
          >
            Block Dates
          </button>
        </div>
      )}

      {isLoading ? (
        <div className="space-y-2">
          <div className="h-8 bg-gray-200 rounded animate-pulse" />
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-10 bg-gray-200 rounded animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="overflow-x-auto border border-gray-200 rounded-lg">
          <table className="min-w-full border-collapse" role="grid" aria-label="Availability calendar">
            <thead>
              <tr className="bg-gray-50">
                <th scope="col" className="sticky left-0 z-10 bg-gray-50 px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b border-r border-gray-200 min-w-[8rem]">
                  Room Type
                </th>
                {days.map((day) => {
                  const dayNum = format(day, 'd')
                  const dayAbbr = format(day, 'EEE')
                  const isCurrentMonth = isSameMonth(day, currentMonth)
                  const isTodayDate = isToday(day)
                  return (
                    <th
                      scope="col"
                      key={day.toISOString()}
                      className={`px-2 py-2 text-center text-xs font-medium border-b border-r border-gray-200 min-w-[3rem] ${
                        isTodayDate
                          ? 'bg-brand-100 text-brand-700'
                          : isCurrentMonth
                            ? 'text-gray-600'
                            : 'text-gray-400'
                      }`}
                      aria-label={`${dayAbbr} ${dayNum}`}
                    >
                      <div>{dayAbbr}</div>
                      <div className={isTodayDate ? 'font-bold' : ''}>{dayNum}</div>
                    </th>
                  )
                })}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {roomTypes.length === 0 ? (
                <tr>
                  <td
                    colSpan={days.length + 1}
                    className="px-4 py-8 text-center text-sm text-gray-500"
                  >
                    No room types found for this property.
                  </td>
                </tr>
              ) : (
                roomTypes.map((rt) => (
                  <tr key={rt.id} className="hover:bg-gray-50">
                    <th scope="row" className="sticky left-0 z-10 bg-white px-3 py-2 text-sm font-medium text-gray-900 border-r border-gray-200">
                      {rt.name}
                    </th>
                    {days.map((day) => {
                      const dateStr = format(day, 'yyyy-MM-dd')
                      const avail = availabilityMap.get(`${rt.id}:${dateStr}`)
                      return (
                        <td key={dateStr} className="px-1 py-1 border-r border-gray-200" role="presentation">
                          <CalendarCell
                            dateStr={dateStr}
                            roomType={rt}
                            availability={avail}
                          />
                        </td>
                      )
                    })}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-4 text-xs text-gray-600">
        <span className="font-medium">Legend:</span>
        <div className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 rounded bg-green-100 border border-green-300" />
          <span>Available (&gt;50%)</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 rounded bg-yellow-100 border border-yellow-300" />
          <span>Low Availability (&gt;0%)</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 rounded bg-red-100 border border-red-300" />
          <span>Fully Booked (0%)</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 rounded bg-gray-200 border border-gray-300" />
          <span>Blocked</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 rounded bg-yellow-200 border border-yellow-400" />
          <span>Hold</span>
        </div>
      </div>

      <BlockDateModal
        isOpen={showBlockModal}
        onClose={() => setShowBlockModal(false)}
        onBlock={(reason, start, end, roomTypeIds) => {
          blockDates({
            property_id: selectedPropertyId,
            room_type_ids: roomTypeIds,
            start_date: start,
            end_date: end,
            reason,
          })
        }}
        roomTypes={roomTypes}
      />
    </div>
  )
}
