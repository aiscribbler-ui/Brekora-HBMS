interface CancellationPolicySnapshot {
  is_non_refundable?: boolean
  free_cancellation_hours?: number | null
  partial_refund_hours?: number | null
  partial_refund_percentage?: number | null
}

interface RefundCalculatorProps {
  totalAmount: number
  policy: CancellationPolicySnapshot | null
  daysUntilCheckIn: number
}

export default function RefundCalculator({ totalAmount, policy, daysUntilCheckIn }: RefundCalculatorProps) {
  const hoursBeforeCheckin = daysUntilCheckIn * 24

  let refundableAmount = 0
  let nonRefundableAmount = totalAmount

  if (!policy || policy.is_non_refundable) {
    refundableAmount = 0
  } else if (
    policy.free_cancellation_hours != null &&
    hoursBeforeCheckin >= policy.free_cancellation_hours
  ) {
    refundableAmount = totalAmount
  } else if (
    policy.partial_refund_hours != null &&
    hoursBeforeCheckin >= policy.partial_refund_hours &&
    policy.partial_refund_percentage != null
  ) {
    refundableAmount = (totalAmount * policy.partial_refund_percentage) / 100
  } else {
    refundableAmount = 0
  }

  nonRefundableAmount = totalAmount - refundableAmount

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-600">Total Amount</span>
        <span className="text-sm font-medium text-gray-900">
          ₹{totalAmount.toFixed(2)}
        </span>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-600">Days Until Check-in</span>
        <span className="text-sm font-medium text-gray-900">{daysUntilCheckIn}</span>
      </div>

      <div className="h-px bg-gray-200" />

      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-green-700">Refundable</span>
        <span className="text-sm font-bold text-green-700">₹{refundableAmount.toFixed(2)}</span>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-red-700">Non-Refundable</span>
        <span className="text-sm font-bold text-red-700">₹{nonRefundableAmount.toFixed(2)}</span>
      </div>

      <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-green-500"
          style={{ width: `${totalAmount > 0 ? (refundableAmount / totalAmount) * 100 : 0}%` }}
        />
      </div>

      <p className="text-xs text-gray-500">
        Refund calculation is based on the cancellation policy effective at the time of booking.
      </p>
    </div>
  )
}
