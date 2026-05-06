import {
  UserPlusIcon,
  ArrowRightOnRectangleIcon,
  HomeIcon,
  ClockIcon,
} from '@heroicons/react/24/outline'

export interface TodayViewProps {
  arrivals: number
  departures: number
  inHouse: number
  pendingCheckIns: number
}

const stats = [
  {
    label: 'Arrivals',
    key: 'arrivals' as const,
    icon: UserPlusIcon,
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    number: 'text-emerald-800',
  },
  {
    label: 'Departures',
    key: 'departures' as const,
    icon: ArrowRightOnRectangleIcon,
    bg: 'bg-orange-50',
    text: 'text-orange-700',
    number: 'text-orange-800',
  },
  {
    label: 'In-House',
    key: 'inHouse' as const,
    icon: HomeIcon,
    bg: 'bg-blue-50',
    text: 'text-blue-700',
    number: 'text-blue-800',
  },
  {
    label: 'Pending Check-ins',
    key: 'pendingCheckIns' as const,
    icon: ClockIcon,
    bg: 'bg-amber-50',
    text: 'text-amber-700',
    number: 'text-amber-800',
  },
]

export default function TodayView({ arrivals, departures, inHouse, pendingCheckIns }: TodayViewProps) {
  const values = { arrivals, departures, inHouse, pendingCheckIns }

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 hover:shadow-md transition-shadow">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Today</h3>
      <div className="grid grid-cols-2 gap-4">
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <div
              key={stat.key}
              className={`${stat.bg} rounded-xl p-3 flex flex-col gap-1`}
            >
              <div className="flex items-center gap-1.5">
                <Icon className={`h-4 w-4 ${stat.text}`} aria-hidden="true" />
                <p className={`text-xs ${stat.text} font-medium`}>{stat.label}</p>
              </div>
              <p className={`text-2xl font-bold ${stat.number}`}>{values[stat.key]}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
