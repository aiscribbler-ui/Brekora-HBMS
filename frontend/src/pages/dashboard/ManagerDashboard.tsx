import TodayView from '@/components/dashboard/TodayView'
import WeekSummary from '@/components/dashboard/WeekSummary'
import OpenTasks from '@/components/dashboard/OpenTasks'
import QuickActions from '@/components/dashboard/QuickActions'
import { useDashboard } from '@/hooks/useDashboard'

export default function ManagerDashboard() {
  const { properties, summary, weekSummary, openTasks, isLoading, error, refresh } = useDashboard()

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">Manager Dashboard</h2>
        <button
          onClick={refresh}
          className="text-sm px-3 py-1.5 bg-brand-600 text-white rounded hover:bg-brand-700 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
          data-testid="refresh-btn"
          aria-label="Refresh dashboard"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 text-red-700 rounded border border-red-200" role="alert">
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white rounded-lg shadow p-5 animate-pulse">
              <div className="h-5 bg-gray-200 rounded w-1/3 mb-4" />
              <div className="grid grid-cols-2 gap-4">
                <div className="h-16 bg-gray-200 rounded" />
                <div className="h-16 bg-gray-200 rounded" />
                <div className="h-16 bg-gray-200 rounded" />
                <div className="h-16 bg-gray-200 rounded" />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div aria-label="Today overview">
            <TodayView
              arrivals={summary.arrivals}
              departures={summary.departures}
              inHouse={summary.inHouse}
              pendingCheckIns={summary.pendingCheckIns}
            />
          </div>
          <div aria-label="Week summary">
            <WeekSummary
              occupancyPercent={weekSummary.occupancyPercent}
              adrByProperty={weekSummary.adrByProperty}
            />
          </div>
          <div aria-label="Open tasks">
            <OpenTasks
              otaQueueReview={openTasks.otaQueueReview}
              paymentFailures={openTasks.paymentFailures}
              pendingRefunds={openTasks.pendingRefunds}
            />
          </div>
          <div aria-label="Quick actions">
            <QuickActions />
          </div>
          <div className="bg-white rounded-lg shadow p-5 md:col-span-2 lg:col-span-2" aria-label="Properties list">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Properties</h3>
            {properties.length === 0 ? (
              <p className="text-sm text-gray-500">No properties found.</p>
            ) : (
              <ul className="divide-y divide-gray-100">
                {properties.map((p) => (
                  <li key={p.id} className="py-2 flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{p.name}</p>
                      <p className="text-xs text-gray-500">{p.address}</p>
                    </div>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        p.status === 'active'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {p.status}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
