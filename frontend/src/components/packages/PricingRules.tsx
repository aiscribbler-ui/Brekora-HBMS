interface PricingRulesData {
  occupancy_scaling?: Record<string, number>
  group_discount?: {
    min_guests?: number
    percentage?: number
  }
  early_bird?: {
    days_before?: number
    percentage?: number
  }
}

interface PricingRulesProps {
  value: PricingRulesData
  onChange: (value: PricingRulesData) => void
}

export default function PricingRules({ value, onChange }: PricingRulesProps) {
  const updateField = <K extends keyof PricingRulesData>(
    key: K,
    subValue: PricingRulesData[K],
  ) => {
    onChange({ ...value, [key]: subValue })
  }

  const updateOccupancyLevel = (level: string, percentage: number) => {
    const scaling = { ...(value.occupancy_scaling || {}) }
    if (!Number.isFinite(percentage) || percentage <= 0) {
      delete scaling[level]
    } else {
      scaling[level] = percentage
    }
    updateField('occupancy_scaling', scaling)
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-3">
        <h3 className="text-sm font-semibold text-gray-900">Occupancy Scaling</h3>
        <p className="text-xs text-gray-500">Set percentage adjustment per occupancy level.</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {['single', 'double', 'triple', 'quad'].map((level) => (
            <div key={level}>
              <label className="block text-xs font-medium text-gray-500 mb-1 capitalize">
                {level} occupancy (%)
              </label>
              <input
                type="number"
                min={-100}
                max={500}
                value={value.occupancy_scaling?.[level] ?? ''}
                onChange={(e) => updateOccupancyLevel(level, parseFloat(e.target.value))}
                placeholder="0"
                className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-3">
        <h3 className="text-sm font-semibold text-gray-900">Group Discount</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Min Guests</label>
            <input
              type="number"
              min={1}
              value={value.group_discount?.min_guests ?? ''}
              onChange={(e) =>
                updateField('group_discount', {
                  ...value.group_discount,
                  min_guests: parseInt(e.target.value) || undefined,
                })
              }
              placeholder="e.g. 4"
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Discount (%)</label>
            <input
              type="number"
              min={0}
              max={100}
              value={value.group_discount?.percentage ?? ''}
              onChange={(e) =>
                updateField('group_discount', {
                  ...value.group_discount,
                  percentage: parseFloat(e.target.value) || undefined,
                })
              }
              placeholder="e.g. 10"
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-3">
        <h3 className="text-sm font-semibold text-gray-900">Early-Bird Discount</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Days Before</label>
            <input
              type="number"
              min={1}
              value={value.early_bird?.days_before ?? ''}
              onChange={(e) =>
                updateField('early_bird', {
                  ...value.early_bird,
                  days_before: parseInt(e.target.value) || undefined,
                })
              }
              placeholder="e.g. 30"
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Discount (%)</label>
            <input
              type="number"
              min={0}
              max={100}
              value={value.early_bird?.percentage ?? ''}
              onChange={(e) =>
                updateField('early_bird', {
                  ...value.early_bird,
                  percentage: parseFloat(e.target.value) || undefined,
                })
              }
              placeholder="e.g. 15"
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
        </div>
      </div>
    </div>
  )
}
