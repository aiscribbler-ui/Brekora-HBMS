import { useEffect, useState } from 'react'
import { fetchFeatureFlags, updateFeatureFlag, type FeatureFlag } from '@/services/adminApi'

function SkeletonRow() {
  return (
    <tr className="border-b border-gray-200 dark:border-gray-700">
      <td className="px-4 py-3">
        <div className="h-4 w-24 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
      </td>
      <td className="px-4 py-3">
        <div className="h-6 w-12 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
      </td>
      <td className="px-4 py-3">
        <div className="h-4 w-48 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
      </td>
    </tr>
  )
}

export default function FeatureFlags() {
  const [flags, setFlags] = useState<FeatureFlag[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    fetchFeatureFlags()
      .then((data) => {
        if (!cancelled) setFlags(data)
      })
      .catch(() => {
        if (!cancelled) setFlags([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const toggleFlag = async (flag: FeatureFlag) => {
    try {
      const updated = await updateFeatureFlag(flag.id, !flag.value)
      setFlags((prev) => prev.map((f) => (f.id === flag.id ? updated : f)))
    } catch {
      // ignore error; interceptor handles auth
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Feature Flags</h2>
      <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300">
                Key
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300">
                Value
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300">
                Description
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-800">
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} />)
            ) : flags.length === 0 ? (
              <tr>
                <td colSpan={3} className="px-4 py-6 text-center text-sm text-gray-500 dark:text-gray-400">
                  No feature flags found.
                </td>
              </tr>
            ) : (
              flags.map((flag) => (
                <tr key={flag.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-gray-100">{flag.key}</td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      aria-label={`Toggle ${flag.key}`}
                      aria-pressed={flag.value}
                      onClick={() => toggleFlag(flag)}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 ${
                        flag.value ? 'bg-brand-600' : 'bg-gray-200 dark:bg-gray-600'
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white dark:bg-gray-100 transition-transform ${
                          flag.value ? 'translate-x-6' : 'translate-x-1'
                        }`}
                      />
                    </button>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{flag.description}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
