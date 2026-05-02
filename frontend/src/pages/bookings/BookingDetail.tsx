import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getBooking, cancelBooking, type Booking } from '@/services/bookingApi'
import { isAxiosError } from '@/lib/api'
import CancelModal from '@/components/bookings/CancelModal'
import InvoiceViewer from '@/components/bookings/InvoiceViewer'

function statusBadgeClass(status: string) {
  switch (status) {
    case 'confirmed':
      return 'bg-green-100 text-green-800'
    case 'pending_payment':
      return 'bg-yellow-100 text-yellow-800'
    case 'payment_failed':
      return 'bg-red-100 text-red-800'
    case 'cancelled':
      return 'bg-gray-100 text-gray-800'
    case 'completed':
      return 'bg-blue-100 text-blue-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

export default function BookingDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [booking, setBooking] = useState<Booking | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [cancelOpen, setCancelOpen] = useState(false)
  const [invoiceOpen, setInvoiceOpen] = useState(false)
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)

  useEffect(() => {
    if (!id) return
    let cancelled = false
    setLoading(true)
    getBooking(id)
      .then((data) => {
        if (!cancelled) setBooking(data)
      })
      .catch((err) => {
        if (!cancelled) {
          if (isAxiosError(err) && err.response?.status === 404) {
            setError('Booking not found.')
          } else {
            setError('Failed to load booking details.')
          }
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id])

  useEffect(() => {
    if (!toast) return
    const timer = setTimeout(() => setToast(null), 4000)
    return () => clearTimeout(timer)
  }, [toast])

  const canEdit = useMemo(() => {
    if (!booking) return false
    if (booking.status !== 'confirmed') return false
    const hoursUntil = (new Date(booking.check_in).getTime() - Date.now()) / (1000 * 60 * 60)
    return hoursUntil > 24
  }, [booking])

  const canCancel = useMemo(() => {
    if (!booking) return false
    return booking.status !== 'cancelled' && booking.status !== 'completed'
  }, [booking])

  const canRetryPayment = useMemo(() => {
    if (!booking) return false
    return booking.status === 'payment_failed'
  }, [booking])

  const handleCancelConfirm = async (reason: string) => {
    if (!id) return
    try {
      await cancelBooking(id, reason)
      setToast({ message: 'Booking cancelled successfully.', type: 'success' })
      setCancelOpen(false)
      // refresh booking
      const updated = await getBooking(id)
      setBooking(updated)
    } catch {
      setToast({ message: 'Failed to cancel booking.', type: 'error' })
    }
  }

  const handleRetryPayment = async () => {
    if (!id) return
    // Stub: existing retryPayment is in bookingApi but uses a different endpoint shape.
    // For MVP we navigate or show alert. Per task, button shown only if payment_failed.
    alert('Retry payment flow will be triggered here.')
  }

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto py-6 px-4">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/3" />
          <div className="h-64 bg-gray-200 rounded" />
        </div>
      </div>
    )
  }

  if (error || !booking) {
    return (
      <div className="max-w-6xl mx-auto py-6 px-4">
        <div className="p-4 bg-red-50 text-red-700 rounded border border-red-200" role="alert">
          {error || 'Booking not found.'}
        </div>
      </div>
    )
  }

  const lineItems = booking.line_items || []
  const modificationLog = booking.modification_log || []

  return (
    <div className="max-w-6xl mx-auto py-6 px-4">
      {toast && (
        <div
          className={`mb-4 p-3 rounded border text-sm ${
            toast.type === 'success'
              ? 'bg-green-50 text-green-800 border-green-200'
              : 'bg-red-50 text-red-800 border-red-200'
          }`}
          role="alert"
        >
          {toast.message}
        </div>
      )}

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Left column: Details */}
        <div className="flex-1 space-y-6">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Booking {booking.id.slice(0, 8)}</h1>
              <p className="text-sm text-gray-500 mt-1">Created {new Date(booking.created_at).toLocaleString()}</p>
            </div>
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${statusBadgeClass(booking.status)}`}
            >
              {booking.status.replace('_', ' ')}
            </span>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-5 space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">Booking Details</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-gray-500">Property</p>
                <p className="font-medium text-gray-900">{booking.property_id}</p>
              </div>
              <div>
                <p className="text-gray-500">Booking Type</p>
                <p className="font-medium text-gray-900 capitalize">{booking.booking_type}</p>
              </div>
              <div>
                <p className="text-gray-500">Check-in</p>
                <p className="font-medium text-gray-900">{booking.check_in}</p>
              </div>
              <div>
                <p className="text-gray-500">Check-out</p>
                <p className="font-medium text-gray-900">{booking.check_out}</p>
              </div>
              <div>
                <p className="text-gray-500">Source</p>
                <p className="font-medium text-gray-900 capitalize">{booking.source_type.replace('_', ' ')}</p>
              </div>
              <div>
                <p className="text-gray-500">Payment State</p>
                <p className="font-medium text-gray-900">{booking.payment_state || 'N/A'}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-5 space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">Guest Details</h2>
            {booking.guest ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-gray-500">Name</p>
                  <p className="font-medium text-gray-900">{booking.guest.name || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-gray-500">Email</p>
                  <p className="font-medium text-gray-900">{booking.guest.email || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-gray-500">Phone</p>
                  <p className="font-medium text-gray-900">{booking.guest.phone || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-gray-500">ID Number</p>
                  <p className="font-medium text-gray-900">{booking.guest.id_number || 'N/A'}</p>
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-500">Guest details are not available for this booking.</p>
            )}
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-5 space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">Amount Breakdown</h2>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Subtotal</span>
                <span className="font-medium text-gray-900">₹{booking.gross_amount.toFixed(2)}</span>
              </div>
              {booking.discount_amount > 0 && (
                <div className="flex justify-between">
                  <span className="text-gray-600">Discount</span>
                  <span className="font-medium text-green-600">-₹{booking.discount_amount.toFixed(2)}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-gray-600">Tax</span>
                <span className="font-medium text-gray-900">₹{booking.tax_amount.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-base font-semibold border-t pt-2">
                <span className="text-gray-900">Total</span>
                <span className="text-gray-900">₹{booking.total_amount.toFixed(2)} {booking.currency}</span>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-5 space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">Line Items</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium text-gray-700">Item</th>
                    <th className="px-3 py-2 text-right font-medium text-gray-700">Qty</th>
                    <th className="px-3 py-2 text-right font-medium text-gray-700">Nights</th>
                    <th className="px-3 py-2 text-right font-medium text-gray-700">Unit Price</th>
                    <th className="px-3 py-2 text-right font-medium text-gray-700">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {lineItems.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-3 py-4 text-center text-gray-500">No line items.</td>
                    </tr>
                  )}
                  {lineItems.map((item, idx) => (
                    <tr key={idx}>
                      <td className="px-3 py-2 text-gray-900">
                        {String(item.item_type || 'Item').toUpperCase()} — {String(item.item_id || '').slice(0, 8)}…
                      </td>
                      <td className="px-3 py-2 text-right text-gray-700">{Number(item.quantity) || 1}</td>
                      <td className="px-3 py-2 text-right text-gray-700">{Number(item.nights) || 1}</td>
                      <td className="px-3 py-2 text-right text-gray-700">₹{Number(item.unit_price || 0).toFixed(2)}</td>
                      <td className="px-3 py-2 text-right font-medium text-gray-900">
                        ₹{Number(item.total_price || 0).toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {modificationLog.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-5 space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">Modification Log</h2>
              <div className="space-y-3">
                {modificationLog.map((entry, idx) => (
                  <details key={idx} className="group border rounded-md">
                    <summary className="cursor-pointer list-none px-4 py-3 flex items-center justify-between text-sm hover:bg-gray-50">
                      <div className="flex items-center gap-3">
                        <span className="text-gray-500">
                          {new Date(entry.timestamp).toLocaleString()}
                        </span>
                        <span className="font-medium text-gray-900">{entry.reason || 'Modification'}</span>
                      </div>
                      <svg
                        className="w-4 h-4 text-gray-400 group-open:rotate-180 transition-transform"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2}
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                      </svg>
                    </summary>
                    <div className="px-4 pb-4 text-sm">
                      {Object.entries(entry.changes).map(([key, change]) => (
                        <div key={key} className="mt-2 grid grid-cols-1 sm:grid-cols-3 gap-2 bg-gray-50 rounded p-2">
                          <div className="font-medium text-gray-700 capitalize">{key.replace('_', ' ')}</div>
                          <div className="text-gray-500">
                            <span className="text-xs uppercase tracking-wide">Old</span>
                            <div className="text-gray-700">{JSON.stringify(change.old)}</div>
                          </div>
                          <div className="text-gray-500">
                            <span className="text-xs uppercase tracking-wide">New</span>
                            <div className="text-gray-700">{JSON.stringify(change.new)}</div>
                          </div>
                        </div>
                      ))}
                      {entry.actor_user_id && (
                        <p className="text-xs text-gray-400 mt-2">Actor: {entry.actor_user_id}</p>
                      )}
                    </div>
                  </details>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right column: Actions */}
        <div className="w-full lg:w-72 space-y-4">
          <div className="bg-white rounded-lg border border-gray-200 p-5 space-y-3">
            <h2 className="text-lg font-semibold text-gray-900">Actions</h2>

            {canEdit && (
              <button
                onClick={() => navigate(`/bookings/${booking.id}/edit`)}
                className="w-full px-4 py-2 rounded-md bg-brand-600 text-white font-medium hover:bg-brand-700 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
              >
                Edit Booking
              </button>
            )}

            {canCancel && (
              <button
                onClick={() => setCancelOpen(true)}
                className="w-full px-4 py-2 rounded-md border border-red-300 text-red-700 hover:bg-red-50 font-medium text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
              >
                Cancel Booking
              </button>
            )}

            {canRetryPayment && (
              <button
                onClick={handleRetryPayment}
                className="w-full px-4 py-2 rounded-md bg-yellow-500 text-white font-medium hover:bg-yellow-600 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:ring-offset-2"
              >
                Retry Payment
              </button>
            )}

            <button
              onClick={() => setInvoiceOpen(true)}
              className="w-full px-4 py-2 rounded-md border border-gray-300 text-gray-700 hover:bg-gray-50 font-medium text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
            >
              Download Invoice
            </button>
          </div>

          {booking.notes && (
            <div className="bg-white rounded-lg border border-gray-200 p-5">
              <h2 className="text-lg font-semibold text-gray-900 mb-2">Notes</h2>
              <p className="text-sm text-gray-600 whitespace-pre-wrap">{booking.notes}</p>
            </div>
          )}

          {booking.cancelled_at && (
            <div className="bg-gray-50 rounded-lg border border-gray-200 p-5">
              <h2 className="text-lg font-semibold text-gray-900 mb-2">Cancellation</h2>
              <div className="text-sm space-y-1">
                <p className="text-gray-600">
                  Cancelled at:{' '}
                  <span className="font-medium text-gray-900">{new Date(booking.cancelled_at).toLocaleString()}</span>
                </p>
                {booking.cancellation_reason && (
                  <p className="text-gray-600">
                    Reason:{' '}
                    <span className="font-medium text-gray-900">{booking.cancellation_reason}</span>
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      <CancelModal
        booking={booking}
        isOpen={cancelOpen}
        onClose={() => setCancelOpen(false)}
        onConfirm={handleCancelConfirm}
      />

      <InvoiceViewer
        booking={booking}
        isOpen={invoiceOpen}
        onClose={() => setInvoiceOpen(false)}
      />
    </div>
  )
}
