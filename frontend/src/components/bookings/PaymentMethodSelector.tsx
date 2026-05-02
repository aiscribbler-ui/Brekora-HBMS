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
      <h3 className="text-lg font-semibold text-gray-900">Payment Method</h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {paymentMethods.map((method) => (
          <label
            key={method.value}
            className={`flex items-center gap-3 rounded-lg border p-4 cursor-pointer transition-colors ${
              selected === method.value
                ? 'border-brand-300 bg-brand-50 ring-1 ring-brand-200'
                : 'border-gray-200 bg-white hover:bg-gray-50'
            }`}
          >
            <input
              type="radio"
              value={method.value}
              {...register('paymentMethod')}
              className="h-4 w-4 text-brand-600 border-gray-300 focus:ring-brand-500"
            />
            <span className="text-sm font-medium text-gray-900">{method.label}</span>
          </label>
        ))}
      </div>

      {errors.paymentMethod && (
        <p className="text-sm text-red-600">{errors.paymentMethod.message}</p>
      )}

      {selected === 'pay_later' && (
        <div className="p-3 bg-yellow-50 text-yellow-800 rounded border border-yellow-200 text-sm">
          Booking will be created with "Pay Later" status. Payment must be collected before check-in.
        </div>
      )}
    </div>
  )
}
