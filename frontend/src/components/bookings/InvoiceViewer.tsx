import type { Booking } from '@/services/bookingApi'

interface InvoiceViewerProps {
  booking: Booking | null
  isOpen: boolean
  onClose: () => void
}

export default function InvoiceViewer({ booking, isOpen, onClose }: InvoiceViewerProps) {
  if (!isOpen || !booking) return null

  const lineItems = booking.line_items || []

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900">Invoice / Receipt</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close invoice"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="px-6 py-6 space-y-6">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm text-gray-500">Booking Reference</p>
              <p className="text-base font-semibold text-gray-900">{booking.id}</p>
            </div>
            <div className="text-right">
              <p className="text-sm text-gray-500">Date</p>
              <p className="text-base font-semibold text-gray-900">
                {new Date(booking.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-500">Check-in</p>
              <p className="text-sm font-medium text-gray-900">{booking.check_in}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Check-out</p>
              <p className="text-sm font-medium text-gray-900">{booking.check_out}</p>
            </div>
          </div>

          <div className="border rounded-lg overflow-hidden">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-gray-700">Item</th>
                  <th className="px-4 py-2 text-right font-medium text-gray-700">Qty</th>
                  <th className="px-4 py-2 text-right font-medium text-gray-700">Nights</th>
                  <th className="px-4 py-2 text-right font-medium text-gray-700">Unit</th>
                  <th className="px-4 py-2 text-right font-medium text-gray-700">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {lineItems.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-4 text-center text-gray-500">No line items.</td>
                  </tr>
                )}
                {lineItems.map((item, idx) => (
                  <tr key={idx}>
                    <td className="px-4 py-2 text-gray-900">
                      {String(item.item_type || 'Item').toUpperCase()} — {String(item.item_id || '').slice(0, 8)}
                    </td>
                    <td className="px-4 py-2 text-right text-gray-700">{Number(item.quantity) || 1}</td>
                    <td className="px-4 py-2 text-right text-gray-700">{Number(item.nights) || 1}</td>
                    <td className="px-4 py-2 text-right text-gray-700">₹{Number(item.unit_price || 0).toFixed(2)}</td>
                    <td className="px-4 py-2 text-right font-medium text-gray-900">
                      ₹{Number(item.total_price || 0).toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Subtotal</span>
              <span className="font-medium text-gray-900">₹{booking.gross_amount.toFixed(2)}</span>
            </div>
            {booking.discount_amount > 0 && (
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Discount</span>
                <span className="font-medium text-green-600">-₹{booking.discount_amount.toFixed(2)}</span>
              </div>
            )}
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Tax</span>
              <span className="font-medium text-gray-900">₹{booking.tax_amount.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-base font-semibold border-t pt-2">
              <span className="text-gray-900">Total</span>
              <span className="text-gray-900">
                ₹{booking.total_amount.toFixed(2)} {booking.currency}
              </span>
            </div>
          </div>
        </div>

        <div className="sticky bottom-0 bg-gray-50 border-t px-6 py-4 flex justify-end">
          <button
            onClick={() => alert('PDF generation coming in Phase 2')}
            className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-md hover:bg-brand-700 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
          >
            Download PDF
          </button>
        </div>
      </div>
    </div>
  )
}
