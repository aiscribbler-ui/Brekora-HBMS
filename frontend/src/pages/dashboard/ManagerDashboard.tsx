import { useNavigate } from 'react-router-dom'
import { RefreshCw, Building2, AlertTriangle, ArrowRight } from 'lucide-react'
import TodayView from '@/components/dashboard/TodayView'
import WeekSummary from '@/components/dashboard/WeekSummary'
import OpenTasks from '@/components/dashboard/OpenTasks'
import QuickActions from '@/components/dashboard/QuickActions'
import { useDashboard } from '@/hooks/useDashboard'

export default function ManagerDashboard() {
  const { properties, summary, weekSummary, openTasks, isLoading, error, refresh } = useDashboard()
  const navigate = useNavigate()

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Manager Dashboard</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            {new Date().toLocaleDateString(undefined, {
              weekday: 'long',
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })}
          </p>
        </div>
        <button
          onClick={refresh}
          className="inline-flex items-center gap-2 text-sm px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 shadow-sm transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
          data-testid="refresh-btn"
          aria-label="Refresh dashboard"
          disabled={isLoading}
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {error && (
        <div
          className="flex items-start gap-3 p-3.5 bg-red-50 text-red-700 rounded-xl border border-red-200"
          role="alert"
        >
          <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Failed to load dashboard</p>
            <p className="text-sm mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 animate-pulse">
              <div className="h-5 bg-gray-200 rounded w-1/3 mb-4" />
              <div className="grid grid-cols-2 gap-3">
                <div className="h-20 bg-gray-100 rounded-xl" />
                <div className="h-20 bg-gray-100 rounded-xl" />
                <div className="h-20 bg-gray-100 rounded-xl" />
                <div className="h-20 bg-gray-100 rounded-xl" />
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
          <div
            className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 md:col-span-2 lg:col-span-2"
            aria-label="Properties list"
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <span
                  className="w-1.5 h-5 bg-gradient-to-b from-brand-500 to-brand-700 rounded-full"
                  aria-hidden="true"
                />
                Properties
              </h3>
              <button
                onClick={() => navigate('/properties')}
                className="text-xs font-medium text-brand-600 hover:text-brand-700 inline-flex items-center gap-1 focus:outline-none focus:ring-2 focus:ring-brand-500 rounded px-1"
              >
                View all
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
            {properties.length === 0 ? (
              <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 px-4 py-8 text-center">
                <Building2 className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                <p className="text-sm text-gray-500">No properties found.</p>
                <button
                  onClick={() => navigate('/properties')}
                  className="mt-3 text-sm text-brand-600 hover:text-brand-700 font-medium"
                >
                  Add a property →
                </button>
              </div>
            ) : (
              <ul className="divide-y divide-gray-100">
                {properties.map((p) => (
                  <li key={p.id} className="py-2.5 flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-brand-50 to-brand-100 text-brand-600 flex items-center justify-center flex-shrink-0">
                        <Building2 className="w-4 h-4" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{p.name}</p>
                        <p className="text-xs text-gray-500 truncate">{p.address}</p>
                      </div>
                    </div>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0 ${
                        p.status === 'active'
                          ? 'bg-emerald-100 text-emerald-700'
                          : 'bg-gray-100 text-gray-600'
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
