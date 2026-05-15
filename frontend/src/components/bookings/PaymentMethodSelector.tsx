import { useFormContext } from 'react-hook-form'
import type { ManualBookingFormData } from '@/pages/bookings/ManualBookingForm'

const paymentMethods = [
  { value: 'cash', label: 'Cash' },
  { value: 'upi', label: 'UPI' },
  { value: 'card', label: 'Card' },
  { value: 'bank_transfer', label: 'Bank Transfer' },
  { value: 'pay_later', label: 'Pay Later' },
] as const

export default function PaymentMethodSelector() {
  const {
    register,
    watch,
    formState: { errors },
  } = useFormContext<ManualBookingFormData>()

  const selected = watch('paymentMethod')

  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Payment Method</h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {paymentMethods.map((method) => (
          <label
            key={method.value}
            className={`flex items-center gap-3 rounded-lg border p-4 cursor-pointer transition-colors ${
              selected === method.value
                ? 'border-brand-300 dark:border-brand-700 bg-brand-50 dark:bg-brand-900/20 ring-1 ring-brand-200 dark:ring-brand-800'
                : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700/50'
            }`}
          >
            <input
              type="radio"
              value={method.value}
              {...register('paymentMethod')}
              className="h-4 w-4 text-brand-600 border-gray-300 dark:border-gray-600 focus:ring-brand-500"
            />
            <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{method.label}</span>
          </label>
        ))}
      </div>

      {errors.paymentMethod && (
        <p className="text-sm text-red-600 dark:text-red-400">{errors.paymentMethod.message}</p>
      )}

      {selected === 'pay_later' && (
        <div className="p-3 bg-warning-light text-warning-dark rounded border border-warning text-sm">
          Booking will be created with "Pay Later" status. Payment must be collected before check-in.
        </div>
      )}
    </div>
  )
}
