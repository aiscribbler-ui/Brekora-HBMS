import type { SearchResultItem } from '@/services/publicApi'

interface PackageCardProps {
  item: SearchResultItem
  onSelect: () => void
}

export default function PackageCard({ item, onSelect }: PackageCardProps) {
  const photo = item.photos?.[0]?.url
  const soldOut = !item.available

  return (
    <div
      className={`relative bg-white dark:bg-gray-800 rounded-xl border overflow-hidden transition-shadow ${
        soldOut ? 'opacity-60 border-gray-200 dark:border-gray-700' : 'border-gray-200 dark:border-gray-700 hover:shadow-md'
      }`}
    >
      <div className="absolute top-3 left-3 z-10">
        <span className="px-2 py-1 bg-purple-600 text-white text-xs font-semibold rounded">
          Package
        </span>
      </div>
      <div className="aspect-[16/10] bg-gray-100 dark:bg-gray-700 relative">
        {photo ? (
          <img
            src={photo}
            alt={item.name}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400 dark:text-gray-500 text-sm">
            No photo
          </div>
        )}
        {soldOut && (
          <div className="absolute inset-0 bg-gray-900/40 flex items-center justify-center">
            <span className="px-3 py-1 bg-gray-900 text-white text-xs font-semibold rounded">
              Sold Out
            </span>
          </div>
        )}
      </div>
      <div className="p-4">
        <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">{item.name}</h3>
        {item.description && (
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400 line-clamp-2">{item.description}</p>
        )}
        <div className="mt-3 flex items-end justify-between">
          <div>
            <span className="text-lg font-bold text-gray-900 dark:text-gray-100">
              ₹{item.price_breakdown.total_amount.toFixed(2)}
            </span>
            <span className="text-xs text-gray-500 dark:text-gray-400 ml-1">
              / {item.price_breakdown.breakdown_per_night.length} night
              {item.price_breakdown.breakdown_per_night.length > 1 ? 's' : ''}
            </span>
          </div>
          <button
            onClick={onSelect}
            disabled={soldOut}
            className="py-2 px-4 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {soldOut ? 'Unavailable' : 'Select'}
          </button>
        </div>
      </div>
    </div>
  )
}
