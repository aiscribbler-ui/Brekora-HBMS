export interface TodayViewProps {
  arrivals: number
  departures: number
  inHouse: number
  pendingCheckIns: number
}

export default function TodayView({ arrivals, departures, inHouse, pendingCheckIns }: TodayViewProps) {
  return (
    <div className="bg-white rounded-lg shadow p-5">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Today</h3>
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-green-50 rounded-md p-3">
          <p className="text-sm text-green-700 font-medium">Arrivals</p>
          <p className="text-2xl font-bold text-green-800">{arrivals}</p>
        </div>
        <div className="bg-orange-50 rounded-md p-3">
          <p className="text-sm text-orange-700 font-medium">Departures</p>
          <p className="text-2xl font-bold text-orange-800">{departures}</p>
        </div>
        <div className="bg-blue-50 rounded-md p-3">
          <p className="text-sm text-blue-700 font-medium">In-House</p>
          <p className="text-2xl font-bold text-blue-800">{inHouse}</p>
        </div>
        <div className="bg-yellow-50 rounded-md p-3">
          <p className="text-sm text-yellow-700 font-medium">Pending Check-ins</p>
          <p className="text-2xl font-bold text-yellow-800">{pendingCheckIns}</p>
        </div>
      </div>
    </div>
  )
}
