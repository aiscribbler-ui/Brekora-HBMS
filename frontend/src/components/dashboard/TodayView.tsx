import { Users, LogOut, Home, Clock } from 'lucide-react'

export interface TodayViewProps {
  arrivals: number
  departures: number
  inHouse: number
  pendingCheckIns: number
}

interface Stat {
  label: string
  value: number
  icon: typeof Users
  bg: string
  iconBg: string
  text: string
  valueText: string
}

export default function TodayView({ arrivals, departures, inHouse, pendingCheckIns }: TodayViewProps) {
  const stats: Stat[] = [
    {
      label: 'Arrivals',
      value: arrivals,
      icon: Users,
      bg: 'bg-emerald-50',
      iconBg: 'bg-emerald-100 text-emerald-600',
      text: 'text-emerald-700',
      valueText: 'text-emerald-900',
    },
    {
      label: 'Departures',
      value: departures,
      icon: LogOut,
      bg: 'bg-orange-50',
      iconBg: 'bg-orange-100 text-orange-600',
      text: 'text-orange-700',
      valueText: 'text-orange-900',
    },
    {
      label: 'In-House',
      value: inHouse,
      icon: Home,
      bg: 'bg-blue-50',
      iconBg: 'bg-blue-100 text-blue-600',
      text: 'text-blue-700',
      valueText: 'text-blue-900',
    },
    {
      label: 'Pending Check-ins',
      value: pendingCheckIns,
      icon: Clock,
      bg: 'bg-amber-50',
      iconBg: 'bg-amber-100 text-amber-600',
      text: 'text-amber-700',
      valueText: 'text-amber-900',
    },
  ]

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 h-full">
      <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <span className="w-1.5 h-5 bg-gradient-to-b from-brand-500 to-brand-700 rounded-full" aria-hidden="true" />
        Today
      </h3>
      <div className="grid grid-cols-2 gap-3">
        {stats.map(({ label, value, icon: Icon, bg, iconBg, text, valueText }) => (
          <div key={label} className={`${bg} rounded-xl p-3 transition-transform hover:scale-[1.02]`}>
            <div className="flex items-center justify-between mb-2">
              <span className={`text-xs font-medium ${text}`}>{label}</span>
              <span
                className={`inline-flex items-center justify-center w-7 h-7 rounded-lg ${iconBg}`}
                aria-hidden="true"
              >
                <Icon className="w-4 h-4" />
              </span>
            </div>
            <p className={`text-2xl font-bold ${valueText}`}>{value}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
