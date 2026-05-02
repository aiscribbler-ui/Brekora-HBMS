import type { ConflictAlternative } from '@/services/bookingApi'

interface ConflictBannerProps {
  message: string
  alternatives?: ConflictAlternative[]
  onSelectAlternative: (alt: ConflictAlternative) => void
}

export default function ConflictBanner({ message, alternatives, onSelectAlternative }: ConflictBannerProps) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-4">
      <div className="flex items-start gap-3">
        <svg
          className="h-5 w-5 text-red-600 mt-0.5 shrink-0"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
        <div className="flex-1">
          <p className="text-sm font-medium text-red-800">{message}</p>
          {alternatives && alternatives.length > 0 && (
            <div className="mt-3 space-y-2">
              <p className="text-xs font-medium text-red-700">Just booked — try these instead:</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {alternatives.map((alt) => (
                  <button
                    key={alt.id}
                    type="button"
                    onClick={() => onSelectAlternative(alt)}
                    className="text-left p-3 bg-white rounded border border-red-200 hover:bg-red-100 text-sm"
                  >
                    <span className="font-medium text-gray-900">{alt.name}</span>
                    <div className="text-xs text-gray-500 mt-1">
                      {alt.check_in} → {alt.check_out}
                    </div>
                    <div className="text-xs text-gray-600 mt-0.5">
                      ₹{alt.price_per_night}/night · {alt.available_count} available
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
