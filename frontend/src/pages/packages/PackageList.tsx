import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PlusIcon, MagnifyingGlassIcon, ArchiveBoxIcon, ArrowPathIcon } from '@heroicons/react/24/outline'
import { getPackages, updatePackage, type Package } from '@/services/packageApi'
import { isAxiosError } from '@/lib/api'

type StatusFilter = 'all' | 'draft' | 'active' | 'archived'

function statusBadge(status: string, isArchived: boolean) {
  if (isArchived) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300">
        Archived
      </span>
    )
  }
  switch (status) {
    case 'active':
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-success-light text-success-dark">
          Active
        </span>
      )
    case 'draft':
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-warning-light text-warning-dark">
          Draft
        </span>
      )
    default:
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300">
          {status}
        </span>
      )
  }
}

function compositionSummary(pkg: Package): string {
  const count = pkg.compositions?.length ?? 0
  if (count === 0) return 'No rooms'
  const totalNights = pkg.compositions.reduce((s, c) => s + c.quantity * c.nights, 0)
  return `${count} room type${count !== 1 ? 's' : ''} · ${totalNights} night${totalNights !== 1 ? 's' : ''}`
}

export default function PackageList() {
  const navigate = useNavigate()
  const [packages, setPackages] = useState<Package[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const fetchPackages = () => {
    let cancelled = false
    setLoading(true)
    setError(null)
    getPackages()
      .then((data) => {
        if (!cancelled) setPackages(data)
      })
      .catch((err) => {
        if (!cancelled) {
          if (isAxiosError(err) && err.response?.data?.detail) {
            setError(err.response.data.detail)
          } else {
            setError('Failed to load packages.')
          }
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }

  useEffect(() => {
    const cleanup = fetchPackages()
    return cleanup
  }, [])

  const filtered = useMemo(() => {
    let result = packages
    const q = search.trim().toLowerCase()
    if (q) {
      result = result.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          (p.description?.toLowerCase().includes(q) ?? false),
      )
    }
    if (statusFilter !== 'all') {
      if (statusFilter === 'archived') {
        result = result.filter((p) => p.is_archived)
      } else {
        result = result.filter((p) => !p.is_archived && p.status === statusFilter)
      }
    }
    return result
  }, [packages, search, statusFilter])

  const activeCount = useMemo(
    () => packages.filter((p) => !p.is_archived && p.status === 'active').length,
    [packages],
  )

  const draftCount = useMemo(
    () => packages.filter((p) => !p.is_archived && p.status === 'draft').length,
    [packages],
  )

  const handleArchiveToggle = async (pkg: Package) => {
    setActionLoading(pkg.id)
    try {
      await updatePackage(pkg.id, {
        is_archived: !pkg.is_archived,
        status: pkg.is_archived ? pkg.status : 'archived',
      })
      setPackages((prev) =>
        prev.map((p) =>
          p.id === pkg.id
            ? { ...p, is_archived: !p.is_archived, status: pkg.is_archived ? p.status : 'archived' }
            : p,
        ),
      )
    } catch (err) {
      if (isAxiosError(err) && err.response?.data?.detail) {
        setError(err.response.data.detail)
      } else {
        setError('Failed to update package.')
      }
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <div className="max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Packages</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {activeCount} active · {draftCount} draft
          </p>
        </div>
        <button
          onClick={() => navigate('/packages/new')}
          className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-md hover:bg-brand-700 transition-colors"
        >
          <PlusIcon className="h-4 w-4" />
          Create Package
        </button>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <div className="relative flex-1">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 dark:text-gray-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search packages..."
            className="w-full pl-9 pr-3 py-2 rounded-md border border-gray-300 dark:border-gray-600 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:bg-gray-800 dark:text-gray-100"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
          className="w-full sm:w-40 rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:bg-gray-800 dark:text-gray-100"
        >
          <option value="all">All Status</option>
          <option value="draft">Draft</option>
          <option value="active">Active</option>
          <option value="archived">Archived</option>
        </select>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded border border-red-200 dark:border-red-800 text-sm" role="alert">
          {error}
        </div>
      )}

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-16 bg-gray-100 dark:bg-gray-700 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <ArchiveBoxIcon className="mx-auto h-10 w-10 text-gray-300 dark:text-gray-600" />
          <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">No packages found.</p>
          {search && (
            <button
              onClick={() => setSearch('')}
              className="mt-2 text-sm text-brand-600 hover:underline"
            >
              Clear search
            </button>
          )}
        </div>
      ) : (
        <>
          {/* Desktop table */}
          <div className="hidden md:block bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Name</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Base Price</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Composition</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {filtered.map((pkg) => (
                  <tr
                    key={pkg.id}
                    onClick={() => navigate(`/packages/${pkg.id}`)}
                    className="hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-gray-100">{pkg.name}</td>
                    <td className="px-4 py-3">{statusBadge(pkg.status, pkg.is_archived)}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">₹{pkg.base_price}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{compositionSummary(pkg)}</td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleArchiveToggle(pkg)
                        }}
                        disabled={actionLoading === pkg.id}
                        className="inline-flex items-center gap-1 text-xs text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 disabled:opacity-50"
                        title={pkg.is_archived ? 'Unarchive' : 'Archive'}
                      >
                        <ArrowPathIcon className="h-3.5 w-3.5" />
                        {pkg.is_archived ? 'Unarchive' : 'Archive'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile cards */}
          <div className="md:hidden space-y-3">
            {filtered.map((pkg) => (
              <button
                key={pkg.id}
                onClick={() => navigate(`/packages/${pkg.id}`)}
                className="w-full text-left bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">{pkg.name}</h3>
                  {statusBadge(pkg.status, pkg.is_archived)}
                </div>
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{compositionSummary(pkg)}</p>
                <p className="mt-1 text-xs text-gray-600 dark:text-gray-400 font-medium">₹{pkg.base_price}</p>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
