import { useEffect, useMemo, useState } from 'react'
import {
  FunnelIcon,
  InboxIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'
import {
  getOtaQueue,
  getOtaQueueItem,
  type ParsedBooking,
  type QueueFilters,
  type OtaSource,
  type QueueStatus,
  type QueueItemDetail,
} from '@/services/otaApi'
import { isAxiosError } from '@/lib/api'
import ParsedBookingCard from '@/components/ota/ParsedBookingCard'
import ConfirmModal from '@/components/ota/ConfirmModal'
import RejectModal from '@/components/ota/RejectModal'
import EditParsedBooking from '@/components/ota/EditParsedBooking'

type Toast = { type: 'success' | 'error'; message: string }

const sourceOptions: { value: OtaSource | ''; label: string }[] = [
  { value: '', label: 'All Sources' },
  { value: 'airbnb', label: 'Airbnb' },
  { value: 'mmt', label: 'MakeMyTrip' },
  { value: 'goibibo', label: 'Goibibo' },
  { value: 'other', label: 'Other' },
]

const statusOptions: { value: QueueStatus | ''; label: string }[] = [
  { value: '', label: 'All Status' },
  { value: 'pending', label: 'Pending' },
  { value: 'confirmed', label: 'Confirmed' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'edited', label: 'Edited' },
]

function sourceBadge(source: OtaSource | string) {
  const styles: Record<string, string> = {
    airbnb: 'bg-rose-100 text-rose-800',
    mmt: 'bg-blue-100 text-blue-800',
    goibibo: 'bg-orange-100 text-orange-800',
    other: 'bg-gray-100 text-gray-800',
  }
  const labels: Record<string, string> = {
    airbnb: 'Airbnb',
    mmt: 'MMT',
    goibibo: 'Goibibo',
    other: 'Other',
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${styles[source] || styles.other}`}>
      {labels[source] || source}
    </span>
  )
}

function statusBadge(status: QueueStatus | string) {
  const styles: Record<string, string> = {
    pending: 'bg-warning-light text-warning-dark',
    confirmed: 'bg-success-light text-success-dark',
    rejected: 'bg-red-100 text-red-800',
    edited: 'bg-blue-100 text-blue-800',
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium capitalize ${styles[status] || 'bg-gray-100 text-gray-800'}`}>
      {status}
    </span>
  )
}

function confidenceDot(score: number) {
  if (score >= 0.95) return 'bg-success'
  if (score >= 0.8) return 'bg-warning'
  return 'bg-red-500'
}

function confidenceLabel(score: number): string {
  if (score >= 0.95) return 'High confidence'
  if (score >= 0.8) return 'Medium confidence'
  return 'Low confidence'
}

const PAGE_SIZE = 10

export default function OtaQueue() {
  const [items, setItems] = useState<ParsedBooking[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [toast, setToast] = useState<Toast | null>(null)

  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [selectedDetail, setSelectedDetail] = useState<QueueItemDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [confirmId, setConfirmId] = useState<string | null>(null)
  const [rejectId, setRejectId] = useState<string | null>(null)
  const [editId, setEditId] = useState<string | null>(null)

  const [sourceFilter, setSourceFilter] = useState<OtaSource | ''>('')
  const [statusFilter, setStatusFilter] = useState<QueueStatus | ''>('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [showFilters, setShowFilters] = useState(false)

  const fetchQueue = () => {
    let cancelled = false
    setLoading(true)
    setError(null)

    const filters: QueueFilters = {
      page,
      page_size: PAGE_SIZE,
    }
    if (sourceFilter) filters.source_type = sourceFilter
    if (statusFilter) filters.status = statusFilter
    if (dateFrom) filters.date_from = dateFrom
    if (dateTo) filters.date_to = dateTo

    getOtaQueue(filters)
      .then((data) => {
        if (!cancelled) {
          setItems(Array.isArray(data?.items) ? data.items : [])
          setTotal(typeof data?.total === 'number' ? data.total : 0)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          if (isAxiosError(err) && err.response?.data?.detail) {
            setError(err.response.data.detail)
          } else {
            setError('Failed to load OTA queue.')
          }
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }

  useEffect(() => {
    const cleanup = fetchQueue()
    return cleanup
  }, [page, sourceFilter, statusFilter, dateFrom, dateTo])

  useEffect(() => {
    if (!toast) return
    const timer = setTimeout(() => setToast(null), 4000)
    return () => clearTimeout(timer)
  }, [toast])

  const selectedBooking = selectedDetail?.parsed_booking ?? null

  const confirmBooking = useMemo(
    () => items.find((b) => b.id === confirmId) || null,
    [items, confirmId],
  )

  const rejectBooking = useMemo(
    () => items.find((b) => b.id === rejectId) || null,
    [items, rejectId],
  )

  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / PAGE_SIZE)), [total])

  const handleSelect = async (id: string | null) => {
    if (!id) {
      setSelectedId(null)
      setSelectedDetail(null)
      setEditId(null)
      return
    }
    setSelectedId(id)
    setEditId(null)
    setDetailLoading(true)
    try {
      const detail = await getOtaQueueItem(id)
      setSelectedDetail(detail)
    } catch {
      const fallback = items.find((b) => b.id === id) || null
      setSelectedDetail(fallback ? { parsed_booking: fallback, raw_email: null, email_link: null } : null)
    } finally {
      setDetailLoading(false)
    }
  }

  const handleActionSuccess = (updated: ParsedBooking) => {
    setItems((prev) => prev.map((b) => (b.id === updated.id ? updated : b)))
    setConfirmId(null)
    setRejectId(null)
    setEditId(null)
    setSelectedDetail((prev) =>
      prev ? { ...prev, parsed_booking: updated } : null
    )
    setToast({ type: 'success', message: `Booking ${updated.guest_name || updated.id} updated successfully.` })
  }

  const handleActionError = (message: string) => {
    setToast({ type: 'error', message })
  }

  const clearFilters = () => {
    setSourceFilter('')
    setStatusFilter('')
    setDateFrom('')
    setDateTo('')
    setPage(1)
  }

  const activeFilterCount = useMemo(() => {
    let count = 0
    if (sourceFilter) count++
    if (statusFilter) count++
    if (dateFrom || dateTo) count++
    return count
  }, [sourceFilter, statusFilter, dateFrom, dateTo])

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">OTA Queue</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {total} parsed booking{total !== 1 ? 's' : ''}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchQueue}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-md bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
          >
            <ArrowPathIcon className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => setShowFilters((s) => !s)}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-md bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
          >
            <FunnelIcon className="h-4 w-4" />
            Filters
            {activeFilterCount > 0 && (
              <span className="inline-flex items-center justify-center px-1.5 py-0.5 rounded-full text-xs font-medium bg-brand-600 text-white">
                {activeFilterCount}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <div
          className={`mb-4 p-3 rounded border text-sm ${
            toast.type === 'success'
              ? 'bg-success-light dark:bg-success-dark/20 text-success dark:text-success-light border-success'
              : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 border-red-200 dark:border-red-800'
          }`}
          role="alert"
        >
          {toast.message}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded border border-red-200 dark:border-red-800 text-sm" role="alert">
          {error}
        </div>
      )}

      {/* Filters */}
      {showFilters && (
        <div className="mb-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label htmlFor="filter-source" className="block text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-1">
              Source
            </label>
            <select
              id="filter-source"
              value={sourceFilter}
              onChange={(e) => { setSourceFilter(e.target.value as OtaSource | ''); setPage(1) }}
              className="block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              {sourceOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="filter-status" className="block text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-1">
              Status
            </label>
            <select
              id="filter-status"
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value as QueueStatus | ''); setPage(1) }}
              className="block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              {statusOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="filter-date-from" className="block text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-1">
              From
            </label>
            <input
              id="filter-date-from"
              type="date"
              value={dateFrom}
              onChange={(e) => { setDateFrom(e.target.value); setPage(1) }}
              className="block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
          <div>
            <label htmlFor="filter-date-to" className="block text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-1">
              To
            </label>
            <div className="flex items-center gap-2">
              <input
                id="filter-date-to"
                type="date"
                value={dateTo}
                onChange={(e) => { setDateTo(e.target.value); setPage(1) }}
                className="block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
              {activeFilterCount > 0 && (
                <button
                  onClick={clearFilters}
                  className="shrink-0 text-xs text-brand-600 hover:underline whitespace-nowrap"
                >
                  Clear
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Loading skeleton */}
      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-16 bg-gray-100 dark:bg-gray-700 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-16 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
          <InboxIcon className="mx-auto h-10 w-10 text-gray-300 dark:text-gray-600" />
          <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">No bookings in queue.</p>
          {activeFilterCount > 0 && (
            <button
              onClick={clearFilters}
              className="mt-2 text-sm text-brand-600 hover:underline"
            >
              Clear filters
            </button>
          )}
        </div>
      ) : (
        <>
          {/* Desktop table */}
          <div className="hidden md:block bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Source</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Guest</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Dates</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Confidence</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {items.map((booking) => (
                  <tr
                    key={booking.id}
                    onClick={() => handleSelect(booking.id === selectedId ? null : booking.id)}
                    className={`hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors ${selectedId === booking.id ? 'bg-brand-50 dark:bg-brand-900/20' : ''}`}
                  >
                    <td className="px-4 py-3">{sourceBadge(booking.source_type)}</td>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-gray-100">{booking.guest_name || '—'}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300">
                      {booking.check_in && booking.check_out
                        ? `${booking.check_in} → ${booking.check_out}`
                        : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span
                          className={`inline-block w-2.5 h-2.5 rounded-full ${confidenceDot(booking.confidence_score)}`}
                          aria-label={confidenceLabel(booking.confidence_score)}
                        />
                        <span className="text-sm text-gray-700 dark:text-gray-300">{(booking.confidence_score * 100).toFixed(0)}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">{statusBadge(booking.status)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile cards */}
          <div className="md:hidden space-y-3">
            {items.map((booking) => (
              <button
                key={booking.id}
                onClick={() => handleSelect(booking.id === selectedId ? null : booking.id)}
                className={`w-full text-left bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors ${selectedId === booking.id ? 'bg-brand-50 dark:bg-brand-900/20 border-brand-200 dark:border-brand-800' : ''}`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {sourceBadge(booking.source_type)}
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{booking.guest_name || '—'}</span>
                  </div>
                  {statusBadge(booking.status)}
                </div>
                <div className="mt-2 flex items-center justify-between text-sm text-gray-600 dark:text-gray-300">
                  <span>
                    {booking.check_in && booking.check_out
                      ? `${booking.check_in} → ${booking.check_out}`
                      : '—'}
                  </span>
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`inline-block w-2 h-2 rounded-full ${confidenceDot(booking.confidence_score)}`}
                      aria-label={confidenceLabel(booking.confidence_score)}
                    />
                    {(booking.confidence_score * 100).toFixed(0)}%
                  </div>
                </div>
              </button>
            ))}
          </div>

          {/* Pagination */}
          <div className="mt-4 flex items-center justify-between">
            <p className="text-sm text-gray-600 dark:text-gray-300">
              Showing {items.length} of {total} result{total !== 1 ? 's' : ''}
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1 || loading}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-md bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
                aria-label="Previous page"
              >
                <ChevronLeftIcon className="h-4 w-4" />
                Prev
              </button>
              <span className="text-sm text-gray-700 dark:text-gray-300 font-medium">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages || loading}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-md bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
                aria-label="Next page"
              >
                Next
                <ChevronRightIcon className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Detail panel */}
          {selectedId && (
            <div className="mt-6">
              {detailLoading ? (
                <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 space-y-4 animate-pulse">
                  <div className="h-6 bg-gray-100 dark:bg-gray-700 rounded w-1/3" />
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="h-10 bg-gray-100 dark:bg-gray-700 rounded" />
                    <div className="h-10 bg-gray-100 dark:bg-gray-700 rounded" />
                    <div className="h-10 bg-gray-100 dark:bg-gray-700 rounded" />
                    <div className="h-10 bg-gray-100 dark:bg-gray-700 rounded" />
                  </div>
                </div>
              ) : selectedBooking ? (
                editId === selectedBooking.id ? (
                  <EditParsedBooking
                    booking={selectedBooking}
                    onSaved={handleActionSuccess}
                    onCancel={() => setEditId(null)}
                    onError={handleActionError}
                  />
                ) : (
                  <ParsedBookingCard
                    booking={selectedBooking}
                    onConfirm={() => setConfirmId(selectedBooking.id)}
                    onEdit={() => setEditId(selectedBooking.id)}
                    onReject={() => setRejectId(selectedBooking.id)}
                    rawEmailUrl={selectedDetail?.email_link || null}
                  />
                )
              ) : null}
            </div>
          )}
        </>
      )}

      <ConfirmModal
        isOpen={!!confirmBooking}
        onClose={() => setConfirmId(null)}
        booking={confirmBooking}
        onSuccess={handleActionSuccess}
        onError={handleActionError}
      />

      <RejectModal
        isOpen={!!rejectBooking}
        onClose={() => setRejectId(null)}
        booking={rejectBooking}
        onSuccess={handleActionSuccess}
        onError={handleActionError}
      />
    </div>
  )
}
