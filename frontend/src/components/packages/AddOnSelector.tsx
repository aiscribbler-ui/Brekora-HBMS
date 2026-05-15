import { useEffect, useMemo, useState } from 'react'
import { getAddOns, type AddOn } from '@/services/packageApi'
import { isAxiosError } from '@/lib/api'

export interface SelectedAddOn {
  add_on_id: string
  quantity: number
  is_included: boolean
}

interface AddOnSelectorProps {
  selectedAddOns: SelectedAddOn[]
  onChange: (addOns: SelectedAddOn[]) => void
}

export default function AddOnSelector({ selectedAddOns, onChange }: AddOnSelectorProps) {
  const [addOns, setAddOns] = useState<AddOn[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getAddOns()
      .then((data) => {
        if (!cancelled) setAddOns(data.filter((a) => !a.is_archived))
      })
      .catch((err) => {
        if (!cancelled) {
          if (isAxiosError(err) && err.response?.data?.detail) {
            setError(err.response.data.detail)
          } else {
            setError('Failed to load add-ons.')
          }
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  const addOnMap = useMemo(() => {
    const map = new Map<string, AddOn>()
    addOns.forEach((a) => map.set(a.id, a))
    return map
  }, [addOns])

  const toggleAddOn = (addOnId: string) => {
    const exists = selectedAddOns.find((s) => s.add_on_id === addOnId)
    if (exists) {
      onChange(selectedAddOns.filter((s) => s.add_on_id !== addOnId))
    } else {
      onChange([...selectedAddOns, { add_on_id: addOnId, quantity: 1, is_included: false }])
    }
  }

  const updateAddOn = (addOnId: string, field: keyof SelectedAddOn, value: number | boolean) => {
    onChange(
      selectedAddOns.map((s) => (s.add_on_id === addOnId ? { ...s, [field]: value } : s)),
    )
  }

  const estimatedAddOnCost = useMemo(() => {
    return selectedAddOns.reduce((sum, s) => {
      if (s.is_included) return sum
      const addon = addOnMap.get(s.add_on_id)
      if (!addon) return sum
      const price = parseFloat(addon.unit_price) || 0
      return sum + s.quantity * price
    }, 0)
  }, [selectedAddOns, addOnMap])

  return (
    <div className="space-y-4">
      {error && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded border border-red-200 dark:border-red-800 text-sm" role="alert">
          {error}
        </div>
      )}

      {loading && (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-12 bg-gray-100 dark:bg-gray-700 rounded-lg animate-pulse" />
          ))}
        </div>
      )}

      {!loading && addOns.length === 0 && (
        <div className="text-center py-8 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <p className="text-sm text-gray-500 dark:text-gray-400">No add-ons available.</p>
        </div>
      )}

      {!loading && addOns.length > 0 && (
        <div className="space-y-3">
          {addOns.map((addon) => {
            const selected = selectedAddOns.find((s) => s.add_on_id === addon.id)
            return (
              <div
                key={addon.id}
                className={`bg-white dark:bg-gray-800 rounded-lg border p-4 transition-colors ${
                  selected ? 'border-brand-300 dark:border-brand-700 ring-1 ring-brand-200 dark:ring-brand-800' : 'border-gray-200 dark:border-gray-700'
                }`}
              >
                <div className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    id={`addon-${addon.id}`}
                    checked={!!selected}
                    onChange={() => toggleAddOn(addon.id)}
                    className="mt-1 h-4 w-4 text-brand-600 border-gray-300 dark:border-gray-600 rounded focus:ring-brand-500"
                  />
                  <div className="flex-1 min-w-0">
                    <label htmlFor={`addon-${addon.id}`} className="block text-sm font-medium text-gray-900 dark:text-gray-100 cursor-pointer">
                      {addon.name}
                      <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">₹{addon.unit_price}</span>
                    </label>
                    {addon.description && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{addon.description}</p>
                    )}
                    {selected && (
                      <div className="mt-3 flex flex-col sm:flex-row gap-3">
                        <div className="w-full sm:w-28">
                          <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Quantity</label>
                          <input
                            type="number"
                            min={1}
                            aria-label="Quantity"
                            value={selected.quantity}
                            onChange={(e) => updateAddOn(addon.id, 'quantity', parseInt(e.target.value) || 1)}
                            className="block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                          />
                        </div>
                        <div className="flex items-center gap-2 pt-5">
                          <input
                            type="checkbox"
                            id={`addon-included-${addon.id}`}
                            checked={selected.is_included}
                            onChange={(e) => updateAddOn(addon.id, 'is_included', e.target.checked)}
                            className="h-4 w-4 text-brand-600 border-gray-300 dark:border-gray-600 rounded focus:ring-brand-500"
                          />
                          <label htmlFor={`addon-included-${addon.id}`} className="text-sm text-gray-700 dark:text-gray-300">
                            Included in package
                          </label>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <div className="text-sm text-gray-600 dark:text-gray-400">
          Estimated add-on cost:{' '}
          <span className="font-semibold text-gray-900 dark:text-gray-100">₹{estimatedAddOnCost.toFixed(2)}</span>
          {selectedAddOns.some((s) => s.is_included) && (
            <span className="text-xs text-gray-500 dark:text-gray-400 ml-2">(some included)</span>
          )}
        </div>
      </div>
    </div>
  )
}
