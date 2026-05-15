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
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white dark:bg-gray-800 border-b dark:border-gray-700 px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">Invoice / Receipt</h2>
          <button
            onClick={onClose}
            className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
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
              <p className="text-sm text-gray-500 dark:text-gray-400">Booking Reference</p>
              <p className="text-base font-semibold text-gray-900 dark:text-gray-100">{booking.id}</p>
            </div>
            <div className="text-right">
              <p className="text-sm text-gray-500 dark:text-gray-400">Date</p>
              <p className="text-base font-semibold text-gray-900 dark:text-gray-100">
                {new Date(booking.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Check-in</p>
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{booking.check_in}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Check-out</p>
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{booking.check_out}</p>
            </div>
          </div>

          <div className="border dark:border-gray-700 rounded-lg overflow-hidden">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-gray-700 dark:text-gray-300">Item</th>
                  <th className="px-4 py-2 text-right font-medium text-gray-700 dark:text-gray-300">Qty</th>
                  <th className="px-4 py-2 text-right font-medium text-gray-700 dark:text-gray-300">Nights</th>
                  <th className="px-4 py-2 text-right font-medium text-gray-700 dark:text-gray-300">Unit</th>
                  <th className="px-4 py-2 text-right font-medium text-gray-700 dark:text-gray-300">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {lineItems.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-4 text-center text-gray-500 dark:text-gray-400">No line items.</td>
                  </tr>
                )}
                {lineItems.map((item, idx) => (
                  <tr key={idx}>
                    <td className="px-4 py-2 text-gray-900 dark:text-gray-100">
                      {String(item.item_type || 'Item').toUpperCase()} — {String(item.item_id || '').slice(0, 8)}
                    </td>
                    <td className="px-4 py-2 text-right text-gray-700 dark:text-gray-300">{Number(item.quantity) || 1}</td>
                    <td className="px-4 py-2 text-right text-gray-700 dark:text-gray-300">{Number(item.nights) || 1}</td>
                    <td className="px-4 py-2 text-right text-gray-700 dark:text-gray-300">₹{Number(item.unit_price || 0).toFixed(2)}</td>
                    <td className="px-4 py-2 text-right font-medium text-gray-900 dark:text-gray-100">
                      ₹{Number(item.total_price || 0).toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">Subtotal</span>
              <span className="font-medium text-gray-900 dark:text-gray-100">₹{booking.gross_amount.toFixed(2)}</span>
            </div>
            {booking.discount_amount > 0 && (
              <div className="flex justify-between text-sm">
                <span className="text-gray-600 dark:text-gray-400">Discount</span>
                <span className="font-medium text-success">-₹{booking.discount_amount.toFixed(2)}</span>
              </div>
            )}
            <div className="flex justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">Tax</span>
              <span className="font-medium text-gray-900 dark:text-gray-100">₹{booking.tax_amount.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-base font-semibold border-t dark:border-gray-700 pt-2">
              <span className="text-gray-900 dark:text-gray-100">Total</span>
              <span className="text-gray-900 dark:text-gray-100">
                ₹{booking.total_amount.toFixed(2)} {booking.currency}
              </span>
            </div>
          </div>
        </div>

        <div className="sticky bottom-0 bg-gray-50 dark:bg-gray-700/50 border-t dark:border-gray-700 px-6 py-4 flex justify-end">
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
