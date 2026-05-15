import { useEffect, useMemo, useState } from 'react'
import { PlusIcon, TrashIcon, HomeIcon } from '@heroicons/react/24/outline'
import { getProperties, getRoomTypes, type Property, type RoomType } from '@/services/propertyApi'
import { isAxiosError } from '@/lib/api'

export interface CompositionItem {
  room_type_id: string
  quantity: number
  nights: number
}

interface RoomCompositionBuilderProps {
  propertyId: string | null
  onPropertyChange: (propertyId: string) => void
  compositions: CompositionItem[]
  onChange: (compositions: CompositionItem[]) => void
}

export default function RoomCompositionBuilder({
  propertyId,
  onPropertyChange,
  compositions,
  onChange,
}: RoomCompositionBuilderProps) {
  const [properties, setProperties] = useState<Property[]>([])
  const [roomTypes, setRoomTypes] = useState<RoomType[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    getProperties()
      .then((data) => {
        if (!cancelled) setProperties(data.filter((p) => !p.is_archived))
      })
      .catch(() => {
        if (!cancelled) setError('Failed to load properties.')
      })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    if (!propertyId) {
      setRoomTypes([])
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    getRoomTypes(propertyId)
      .then((data) => {
        if (!cancelled) setRoomTypes(data.filter((r) => r.is_active && !r.is_archived))
      })
      .catch((err) => {
        if (!cancelled) {
          if (isAxiosError(err) && err.response?.data?.detail) {
            setError(err.response.data.detail)
          } else {
            setError('Failed to load room types.')
          }
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [propertyId])

  const roomTypeMap = useMemo(() => {
    const map = new Map<string, RoomType>()
    roomTypes.forEach((rt) => map.set(rt.id, rt))
    return map
  }, [roomTypes])

  const totalRoomNights = useMemo(() => {
    return compositions.reduce((sum, comp) => sum + comp.quantity * comp.nights, 0)
  }, [compositions])

  const estimatedRoomCost = useMemo(() => {
    return compositions.reduce((sum, comp) => {
      const rt = roomTypeMap.get(comp.room_type_id)
      if (!rt) return sum
      const rate = parseFloat(rt.default_rate) || 0
      return sum + comp.quantity * comp.nights * rate
    }, 0)
  }, [compositions, roomTypeMap])

  const availableRoomTypes = useMemo(() => {
    const usedIds = new Set(compositions.map((c) => c.room_type_id))
    return roomTypes.filter((rt) => !usedIds.has(rt.id))
  }, [roomTypes, compositions])

  const addComposition = () => {
    if (availableRoomTypes.length === 0) return
    const first = availableRoomTypes[0]
    onChange([...compositions, { room_type_id: first.id, quantity: 1, nights: 1 }])
  }

  const updateComposition = (index: number, field: keyof CompositionItem, value: string | number) => {
    const next = [...compositions]
    next[index] = { ...next[index], [field]: value }
    onChange(next)
  }

  const removeComposition = (index: number) => {
    const next = [...compositions]
    next.splice(index, 1)
    onChange(next)
  }

  return (
    <div className="space-y-4">
      <div>
        <label htmlFor="property-select" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Property
        </label>
        <div className="mt-1 relative">
          <HomeIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 dark:text-gray-500" />
          <select
            id="property-select"
            value={propertyId ?? ''}
            onChange={(e) => onPropertyChange(e.target.value)}
            className="block w-full rounded-md border border-gray-300 dark:border-gray-600 pl-9 pr-3 py-2 text-sm shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          >
            <option value="">Select a property...</option>
            {properties.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded border border-red-200 dark:border-red-800 text-sm" role="alert">
          {error}
        </div>
      )}

      {loading && (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-16 bg-gray-100 dark:bg-gray-700 rounded-lg animate-pulse" />
          ))}
        </div>
      )}

      {!loading && propertyId && roomTypes.length === 0 && (
        <div className="text-center py-8 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <p className="text-sm text-gray-500 dark:text-gray-400">No active room types found for this property.</p>
        </div>
      )}

      {!loading && roomTypes.length > 0 && (
        <div className="space-y-3">
          {compositions.map((comp, idx) => {
            return (
              <div
                key={idx}
                className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 flex flex-col sm:flex-row sm:items-center gap-4"
              >
                <div className="flex-1">
                  <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Room Type</label>
                  <select
                    value={comp.room_type_id}
                    onChange={(e) => updateComposition(idx, 'room_type_id', e.target.value)}
                    className="block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  >
                    <option value="">Select room type...</option>
                    {roomTypes.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name} (₹{r.default_rate}/night)
                      </option>
                    ))}
                  </select>
                </div>
                <div className="w-full sm:w-28">
                  <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Quantity</label>
                  <input
                    type="number"
                    min={1}
                    aria-label="Quantity"
                    value={comp.quantity}
                    onChange={(e) => updateComposition(idx, 'quantity', parseInt(e.target.value) || 1)}
                    className="block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>
                <div className="w-full sm:w-28">
                  <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Nights</label>
                  <input
                    type="number"
                    min={1}
                    aria-label="Nights"
                    value={comp.nights}
                    onChange={(e) => updateComposition(idx, 'nights', parseInt(e.target.value) || 1)}
                    className="block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>
                <div className="flex items-end">
                  <button
                    type="button"
                    onClick={() => removeComposition(idx)}
                    className="p-2 text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md transition-colors"
                    aria-label="Remove room type"
                  >
                    <TrashIcon className="h-5 w-5" />
                  </button>
                </div>
              </div>
            )
          })}

          {availableRoomTypes.length > 0 && (
            <button
              type="button"
              onClick={addComposition}
              className="inline-flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 text-brand-600 dark:text-brand-400 border border-brand-200 dark:border-brand-800 text-sm font-medium rounded-md hover:bg-brand-50 dark:hover:bg-brand-900/20 transition-colors"
            >
              <PlusIcon className="h-4 w-4" />
              Add Room Type
            </button>
          )}

          {compositions.length === 0 && (
            <button
              type="button"
              onClick={addComposition}
              className="inline-flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 text-brand-600 dark:text-brand-400 border border-brand-200 dark:border-brand-800 text-sm font-medium rounded-md hover:bg-brand-50 dark:hover:bg-brand-900/20 transition-colors"
            >
              <PlusIcon className="h-4 w-4" />
              Add Room Type
            </button>
          )}
        </div>
      )}

      <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div className="text-sm text-gray-600 dark:text-gray-400">
            Total room nights: <span className="font-semibold text-gray-900 dark:text-gray-100">{totalRoomNights}</span>
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-400">
            Estimated room cost: <span className="font-semibold text-gray-900 dark:text-gray-100">₹{estimatedRoomCost.toFixed(2)}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
