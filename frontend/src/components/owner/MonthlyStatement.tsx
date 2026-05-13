import { useState, useMemo } from 'react'
import type { Statement } from '@/services/ownerApi'

const inr = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' })

interface Props {
  data: Statement
}

type SortKey = 'booking_id' | 'source' | 'gross_amount' | 'ota_commission' | 'partner_commission' | 'gst' | 'net_amount'
type SortDir = 'asc' | 'desc'

export default function MonthlyStatement({ data }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('booking_id')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [page, setPage] = useState(1)
  const pageSize = 10

  const sorted = useMemo(() => {
    const list = [...data.bookings]
    list.sort((a, b) => {
      const aVal = a[sortKey]
      const bVal = b[sortKey]
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDir === 'asc' ? aVal - bVal : bVal - aVal
      }
      return sortDir === 'asc'
        ? String(aVal).localeCompare(String(bVal))
        : String(bVal).localeCompare(String(aVal))
    })
    return list
  }, [data.bookings, sortKey, sortDir])

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize))
  const paged = sorted.slice((page - 1) * pageSize, page * pageSize)

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
    setPage(1)
  }

  const handleDownload = () => {
    alert('PDF generation coming in Phase 2')
  }

  const columns: { key: SortKey; label: string }[] = [
    { key: 'booking_id', label: 'Booking ID' },
    { key: 'source', label: 'Source' },
    { key: 'gross_amount', label: 'Gross' },
    { key: 'ota_commission', label: 'OTA Comm.' },
    { key: 'partner_commission', label: 'Partner Comm.' },
    { key: 'gst', label: 'GST' },
    { key: 'net_amount', label: 'Net' },
  ]

  return (
    <div className="rounded-xl bg-white shadow-sm border border-gray-200 dark:border-gray-700 dark:bg-gray-800 overflow-hidden">
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Monthly Statement</h3>
        <button
          onClick={handleDownload}
          className="text-sm px-3 py-1.5 bg-brand-600 text-white rounded hover:bg-brand-700 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          Download PDF
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm text-left">
          <thead className="bg-gray-50 dark:bg-gray-700 text-gray-500 dark:text-gray-300 uppercase text-xs">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className="px-4 py-3 font-medium cursor-pointer select-none hover:text-gray-700 dark:hover:text-gray-100"
                  onClick={() => toggleSort(col.key)}
                >
                  <span className="flex items-center gap-1">
                    {col.label}
                    {sortKey === col.key && (
                      <span className="text-xs">{sortDir === 'asc' ? '▲' : '▼'}</span>
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {paged.map((b) => (
              <tr key={b.booking_id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">{b.booking_id}</td>
                <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{b.source}</td>
                <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{inr.format(b.gross_amount)}</td>
                <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{inr.format(b.ota_commission)}</td>
                <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{inr.format(b.partner_commission)}</td>
                <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{inr.format(b.gst)}</td>
                <td className="px-4 py-3 font-semibold text-gray-900 dark:text-gray-100">{inr.format(b.net_amount)}</td>
              </tr>
            ))}
            {paged.length === 0 && (
              <tr>
                <td colSpan={columns.length} className="px-4 py-6 text-center text-gray-500 dark:text-gray-400">
                  No bookings found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 dark:border-gray-700">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Page {page} of {totalPages}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1 text-xs rounded border border-gray-300 dark:border-gray-600 disabled:opacity-50 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Prev
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-3 py-1 text-xs rounded border border-gray-300 dark:border-gray-600 disabled:opacity-50 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
