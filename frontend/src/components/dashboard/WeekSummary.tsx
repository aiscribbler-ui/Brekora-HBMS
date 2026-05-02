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
    <div className="bg-white rounded-lg shadow p-5">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">This Week</h3>
      <div className="mb-4">
        <p className="text-sm text-gray-600">Occupancy</p>
        <div className="flex items-center gap-3 mt-1">
          <div className="flex-1 h-3 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-brand-600 rounded-full transition-all duration-500"
              style={{ width: `${occupancyPercent}%` }}
              data-testid="occupancy-bar"
            />
          </div>
          <span className="text-lg font-bold text-gray-900">{occupancyPercent}%</span>
        </div>
      </div>
      <div>
        <p className="text-sm text-gray-600 mb-2">ADR by Property</p>
        {adrByProperty.length === 0 ? (
          <p className="text-sm text-gray-400 italic">No data available</p>
        ) : (
          <ul className="space-y-2">
            {adrByProperty.map((item) => (
              <li key={item.propertyId} className="flex justify-between items-center text-sm">
                <span className="text-gray-700">{item.propertyName}</span>
                <span className="font-semibold text-gray-900">₹{item.adr.toLocaleString()}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
