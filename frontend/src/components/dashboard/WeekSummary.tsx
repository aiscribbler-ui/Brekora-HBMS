import { BarChart3 } from 'lucide-react'

export interface AdrByProperty {
  propertyId: string
  propertyName: string
  adr: number
}

export interface WeekSummaryProps {
  occupancyPercent: number
  adrByProperty: AdrByProperty[]
}

export default function WeekSummary({ occupancyPercent, adrByProperty }: WeekSummaryProps) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 hover:shadow-md transition-shadow">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">This Week</h3>
      <div className="mb-5">
        <p className="text-sm text-gray-600 mb-1">Occupancy</p>
        <div className="flex items-center gap-3 mt-1">
          <div className="flex-1 h-3 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700 bg-gradient-to-r from-brand-500 to-brand-700"
              style={{ width: `${occupancyPercent}%` }}
              data-testid="occupancy-bar"
              role="progressbar"
              aria-valuenow={occupancyPercent}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>
          <span className="text-lg font-bold text-gray-900 w-12 text-right">{occupancyPercent}%</span>
        </div>
      </div>
      <div>
        <p className="text-sm text-gray-600 mb-2 flex items-center gap-1.5">
          <BarChart3 className="w-4 h-4 text-brand-500" />
          ADR by Property
        </p>
        {adrByProperty.length === 0 ? (
          <div className="py-4 text-center">
            <p className="text-sm text-gray-400">No pricing data yet</p>
            <p className="text-xs text-gray-300 mt-1">Bookings will populate this section</p>
          </div>
        ) : (
          <ul className="space-y-1.5">
            {adrByProperty.map((item) => (
              <li
                key={item.propertyId}
                className="flex justify-between items-center text-sm px-2.5 py-2 rounded-md hover:bg-gray-50 transition-colors"
              >
                <span className="text-gray-700 truncate">{item.propertyName}</span>
                <span className="font-semibold text-gray-900 tabular-nums">
                  ₹{item.adr.toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
