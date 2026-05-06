import { useNavigate } from 'react-router-dom'
import { RefreshCw, Building2, AlertTriangle, ArrowRight } from 'lucide-react'
import TodayView from '@/components/dashboard/TodayView'
import WeekSummary from '@/components/dashboard/WeekSummary'
import OpenTasks from '@/components/dashboard/OpenTasks'
import QuickActions from '@/components/dashboard/QuickActions'
import { useDashboard } from '@/hooks/useDashboard'
import { ArrowPathIcon, BuildingOfficeIcon } from '@heroicons/react/24/outline'

export default function ManagerDashboard() {
  const { properties, summary, weekSummary, openTasks, isLoading, error, refresh } = useDashboard()
  const navigate = useNavigate()

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Manager Dashboard</h2>
          <p className="text-sm text-gray-500 mt-1">Overview of today's operations and pending tasks</p>
        </div>
        <button
          onClick={refresh}
          className="inline-flex items-center gap-2 text-sm px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 shadow-sm"
          data-testid="refresh-btn"
          aria-label="Refresh dashboard"
          disabled={isLoading}
        >
          <ArrowPathIcon className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-xl border border-red-200 flex items-center gap-2" role="alert">
          <span className="font-medium">Error:</span> {error}
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 animate-pulse">
              <div className="h-5 bg-gray-200 rounded w-1/3 mb-4" />
              <div className="grid grid-cols-2 gap-4">
                <div className="h-16 bg-gray-200 rounded-xl" />
                <div className="h-16 bg-gray-200 rounded-xl" />
                <div className="h-16 bg-gray-200 rounded-xl" />
                <div className="h-16 bg-gray-200 rounded-xl" />
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
          <div aria-label="Quick actions" className="md:col-span-2 lg:col-span-1">
            <QuickActions />
          </div>
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 md:col-span-2 lg:col-span-2 hover:shadow-md transition-shadow" aria-label="Properties list">
            <div className="flex items-center gap-2 mb-4">
              <BuildingOfficeIcon className="h-5 w-5 text-brand-600" aria-hidden="true" />
              <h3 className="text-lg font-semibold text-gray-900">Properties</h3>
            </div>
            {properties.length === 0 ? (
              <div className="py-6 text-center">
                <BuildingOfficeIcon className="h-10 w-10 text-gray-300 mx-auto mb-2" aria-hidden="true" />
                <p className="text-sm text-gray-500">No properties found.</p>
                <p className="text-xs text-gray-400 mt-1">Add your first property to get started</p>
              </div>
            ) : (
              <ul className="divide-y divide-gray-100">
                {properties.map((p) => (
                  <li key={p.id} className="py-3 flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{p.name}</p>
                      <p className="text-xs text-gray-500">{p.address}</p>
                    </div>
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        p.status === 'active'
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      <span
                        className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
                          p.status === 'active' ? 'bg-emerald-500' : 'bg-gray-400'
                        }`}
                        aria-hidden="true"
                      />
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
