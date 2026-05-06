import { TrendingUp, BarChart3 } from 'lucide-react'

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
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 h-full">
      <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <span className="w-1.5 h-5 bg-gradient-to-b from-brand-500 to-brand-700 rounded-full" aria-hidden="true" />
        This Week
      </h3>
      <div className="mb-5">
        <div className="flex items-center justify-between mb-2">
          <p className="text-sm text-gray-600 flex items-center gap-1.5">
            <TrendingUp className="w-4 h-4 text-brand-500" />
            Occupancy
          </p>
          <span className="text-2xl font-bold text-gray-900">{occupancyPercent}%</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex-1 h-3 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-brand-500 to-brand-700 rounded-full transition-all duration-500 shadow-sm"
              style={{ width: `${Math.max(0, Math.min(100, occupancyPercent))}%` }}
              data-testid="occupancy-bar"
              role="progressbar"
              aria-valuenow={occupancyPercent}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>
        </div>
      </div>
      <div>
        <p className="text-sm text-gray-600 mb-2 flex items-center gap-1.5">
          <BarChart3 className="w-4 h-4 text-brand-500" />
          ADR by Property
        </p>
        {adrByProperty.length === 0 ? (
          <div className="rounded-lg border border-dashed border-gray-200 bg-gray-50 px-3 py-4 text-center">
            <p className="text-xs text-gray-500">No ADR data yet</p>
            <p className="text-[11px] text-gray-400 mt-0.5">Bookings will populate this view</p>
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
