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
    bg: 'bg-success-light',
    text: 'text-success',
    number: 'text-success-dark',
  },
  {
    label: 'Departures',
    key: 'departures' as const,
    icon: ArrowRightOnRectangleIcon,
    bg: 'bg-secondary-light',
    text: 'text-secondary',
    number: 'text-secondary-dark',
  },
  {
    label: 'In-House',
    key: 'inHouse' as const,
    icon: HomeIcon,
    bg: 'bg-info-light',
    text: 'text-info',
    number: 'text-info-dark',
  },
  {
    label: 'Pending Check-ins',
    key: 'pendingCheckIns' as const,
    icon: ClockIcon,
    bg: 'bg-warning-light',
    text: 'text-warning',
    number: 'text-warning-dark',
  },
]

export default function TodayView({ arrivals, departures, inHouse, pendingCheckIns }: TodayViewProps) {
  const values = { arrivals, departures, inHouse, pendingCheckIns }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-5 hover:shadow-md transition-shadow">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Today</h2>
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
