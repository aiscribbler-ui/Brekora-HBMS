import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { getProperties, type Property } from '@/services/propertyApi'
import { getPnl, getPayout, getStatement } from '@/services/ownerApi'
import type { PnLSummary as PnLSummaryType, PayoutRecord, Statement } from '@/services/ownerApi'
import PnLSummary from '@/components/owner/PnLSummary'
import PayoutHistory from '@/components/owner/PayoutHistory'
import MonthlyStatement from '@/components/owner/MonthlyStatement'

function getDefaultMonth(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

export default function OwnerDashboard() {
  const user = useAuthStore((s) => s.user)
  const navigate = useNavigate()

  const [properties, setProperties] = useState<Property[]>([])
  const [selectedPropertyId, setSelectedPropertyId] = useState<string>('')
  const [month, setMonth] = useState<string>(getDefaultMonth())
  const [pnl, setPnl] = useState<PnLSummaryType | null>(null)
  const [payout, setPayout] = useState<PayoutRecord | null>(null)
  const [statement, setStatement] = useState<Statement | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hasGenerated, setHasGenerated] = useState(false)

  useEffect(() => {
    let cancelled = false
    getProperties()
      .then((data) => {
        if (cancelled) return
        setProperties(data)
        if (data.length > 0) {
          setSelectedPropertyId((prev) => prev || data[0].id)
        }
      })
      .catch(() => {
        if (!cancelled) setError('Failed to load properties.')
      })
    return () => {
      cancelled = true
    }
  }, [])

  const generateReport = useCallback(async () => {
    if (!selectedPropertyId) {
      setError('Please select a property.')
      return
    }
    setIsLoading(true)
    setError(null)
    setHasGenerated(false)
    try {
      const [pnlData, payoutData, statementData] = await Promise.all([
        getPnl(selectedPropertyId, month),
        getPayout(selectedPropertyId, month),
        getStatement(selectedPropertyId, month),
      ])
      setPnl(pnlData)
      setPayout(payoutData)
      setStatement(statementData)
      setHasGenerated(true)
    } catch {
      setError('Failed to generate report. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }, [selectedPropertyId, month])

  useEffect(() => {
    if (!user || (user.role !== 'Owner' && user.role !== 'Admin')) {
      const timer = setTimeout(() => navigate('/', { replace: true }), 3000)
      return () => clearTimeout(timer)
    }
  }, [user, navigate])

  if (!user || (user.role !== 'Owner' && user.role !== 'Admin')) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">Access Denied</h1>
          <p className="mt-2 text-gray-600">You do not have permission to view this page.</p>
          <p className="mt-1 text-sm text-gray-500">Redirecting to home...</p>
          <button
            onClick={() => navigate('/')}
            className="mt-4 inline-flex rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            Go Home
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">Owner Reports</h2>

      <div className="flex flex-col md:flex-row gap-4 items-start md:items-end">
        <div className="flex flex-col gap-1 w-full md:w-auto">
          <label htmlFor="property-select" className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Property
          </label>
          <select
            id="property-select"
            value={selectedPropertyId}
            onChange={(e) => setSelectedPropertyId(e.target.value)}
            className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="" disabled>
              Select property
            </option>
            {properties.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1 w-full md:w-auto">
          <label htmlFor="month-select" className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Month
          </label>
          <input
            id="month-select"
            type="month"
            value={month}
            onChange={(e) => setMonth(e.target.value)}
            className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        <button
          onClick={generateReport}
          disabled={isLoading}
          className="w-full md:w-auto px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-md hover:bg-brand-700 disabled:opacity-60 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          {isLoading ? 'Generating...' : 'Generate Report'}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 text-red-700 rounded border border-red-200" role="alert">
          {error}
        </div>
      )}

      {isLoading && (
        <div className="space-y-4 animate-pulse">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-20 bg-gray-200 dark:bg-gray-700 rounded" />
            ))}
          </div>
          <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded" />
          <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded" />
        </div>
      )}

      {!isLoading && hasGenerated && pnl && (
        <section aria-label="Profit and loss summary">
          <PnLSummary data={pnl} />
        </section>
      )}

      {!isLoading && hasGenerated && payout && (
        <section aria-label="Revenue split" className="max-w-xl">
          <PayoutHistory data={payout} />
        </section>
      )}

      {!isLoading && hasGenerated && statement && (
        <section aria-label="Monthly statement">
          <MonthlyStatement data={statement} />
        </section>
      )}
    </div>
  )
}
