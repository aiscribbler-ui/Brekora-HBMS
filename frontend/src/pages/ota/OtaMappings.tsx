import { useState, useEffect, useCallback } from 'react'
import { useAuthStore } from '@/store/authStore'
import {
  listOtaMappings,
  createOtaMapping,
  updateOtaMapping,
  deleteOtaMapping,
  type OtaMappingListItem,
  type OtaMappingCreatePayload,
} from '@/services/otaApi'
import { getProperties, getRoomTypes, type Property, type RoomType } from '@/services/propertyApi'
import { PlusIcon, PencilIcon, TrashIcon, LinkIcon } from '@heroicons/react/24/outline'

const SOURCE_OPTIONS = ['airbnb', 'mmt', 'goibibo', 'bookingcom', 'other']

export default function OtaMappings() {
  const user = useAuthStore((s) => s.user)
  const [mappings, setMappings] = useState<OtaMappingListItem[]>([])
  const [properties, setProperties] = useState<Property[]>([])
  const [roomTypes, setRoomTypes] = useState<RoomType[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)

  const [form, setForm] = useState<OtaMappingCreatePayload>({
    ota_source: 'airbnb',
    listing_id: '',
    room_type_id: '',
    property_id: '',
    is_active: true,
  })

  const canManage = user?.role === 'Admin' || user?.role === 'ListingManager'

  const loadData = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const [mData, pData] = await Promise.all([listOtaMappings(), getProperties()])
      setMappings(mData.filter((m) => !m.is_archived))
      setProperties(pData)
    } catch {
      setError('Failed to load OTA mappings.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const resetForm = () => {
    setForm({
      ota_source: 'airbnb',
      listing_id: '',
      room_type_id: '',
      property_id: '',
      is_active: true,
    })
    setEditingId(null)
    setShowForm(false)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      if (editingId) {
        await updateOtaMapping(editingId, form)
      } else {
        await createOtaMapping(form)
      }
      resetForm()
      await loadData()
    } catch (err: unknown) {
      const msg = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : null
      setError(msg || 'Failed to save mapping.')
    }
  }

  const handleEdit = (m: OtaMappingListItem) => {
    setForm({
      ota_source: m.ota_source,
      listing_id: m.listing_id,
      room_type_id: m.room_type_id,
      property_id: m.property_id,
      is_active: m.is_active,
    })
    setEditingId(m.id)
    setShowForm(true)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this mapping?')) return
    setError(null)
    try {
      await deleteOtaMapping(id)
      await loadData()
    } catch {
      setError('Failed to delete mapping.')
    }
  }

  useEffect(() => {
    let cancelled = false
    if (!form.property_id) {
      setRoomTypes([])
      return
    }
    getRoomTypes(form.property_id)
      .then((data) => {
        if (!cancelled) setRoomTypes(data)
      })
      .catch(() => {
        if (!cancelled) setRoomTypes([])
      })
    return () => {
      cancelled = true
    }
  }, [form.property_id])

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">OTA Mappings</h1>
          <p className="text-sm text-gray-500 mt-1">Link your properties and room types to external OTA listings</p>
        </div>
        {canManage && (
          <button
            onClick={() => {
              setShowForm(!showForm)
              if (showForm) resetForm()
            }}
            className="inline-flex items-center gap-2 text-sm px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 shadow-sm"
          >
            <PlusIcon className="h-4 w-4" />
            {showForm ? 'Cancel' : 'Add Mapping'}
          </button>
        )}
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-xl border border-red-200 flex items-center gap-2" role="alert">
          <span className="font-medium">Error:</span> {error}
        </div>
      )}

      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-4"
        >
          <h2 className="text-lg font-semibold text-gray-900">{editingId ? 'Edit Mapping' : 'New Mapping'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Property</label>
              <select
                required
                value={form.property_id}
                onChange={(e) => setForm((f) => ({ ...f, property_id: e.target.value, room_type_id: '' }))}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                <option value="" disabled>Select property</option>
                {properties.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Room Type</label>
              <select
                required
                value={form.room_type_id}
                onChange={(e) => setForm((f) => ({ ...f, room_type_id: e.target.value }))}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                disabled={!form.property_id}
              >
                <option value="" disabled>Select room type</option>
                {roomTypes.length === 0 && <option value="" disabled>No room types</option>}
                {roomTypes.map((rt) => (
                  <option key={rt.id} value={rt.id}>{rt.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">OTA Source</label>
              <select
                required
                value={form.ota_source}
                onChange={(e) => setForm((f) => ({ ...f, ota_source: e.target.value }))}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                {SOURCE_OPTIONS.map((s) => (
                  <option key={s} value={s}>{s.toUpperCase()}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">External Listing ID</label>
              <input
                type="text"
                required
                value={form.listing_id}
                onChange={(e) => setForm((f) => ({ ...f, listing_id: e.target.value }))}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder="e.g., 12345678"
              />
            </div>

            <div className="flex items-center gap-2 md:col-span-2">
              <input
                id="is_active"
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
                className="h-4 w-4 text-brand-600 border-gray-300 rounded focus:ring-brand-500"
              />
              <label htmlFor="is_active" className="text-sm text-gray-700">Active</label>
            </div>
          </div>

          <div className="flex gap-3">
            <button
              type="submit"
              className="px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              {editingId ? 'Update Mapping' : 'Create Mapping'}
            </button>
            <button
              type="button"
              onClick={resetForm}
              className="px-4 py-2 bg-white text-gray-700 border border-gray-300 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {isLoading ? (
        <div className="space-y-3 animate-pulse">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-16 bg-gray-200 rounded-xl" />
          ))}
        </div>
      ) : mappings.length === 0 ? (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-10 text-center">
          <LinkIcon className="h-10 w-10 text-gray-300 mx-auto mb-2" />
          <p className="text-sm text-gray-500">No OTA mappings found.</p>
          <p className="text-xs text-gray-400 mt-1">Add your first mapping to link external listings</p>
        </div>
      ) : (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-100">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Property</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Room Type</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Source</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Listing ID</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {mappings.map((m) => (
                  <tr key={m.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 text-sm text-gray-900">{m.property?.name || m.property_id}</td>
                    <td className="px-4 py-3 text-sm text-gray-900">{m.room_type?.name || m.room_type_id}</td>
                    <td className="px-4 py-3 text-sm text-gray-700 capitalize">{m.ota_source}</td>
                    <td className="px-4 py-3 text-sm text-gray-700 font-mono">{m.listing_id}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          m.is_active
                            ? 'bg-emerald-100 text-emerald-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {m.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {canManage && (
                          <>
                            <button
                              onClick={() => handleEdit(m)}
                              className="p-1.5 text-gray-500 hover:text-brand-600 hover:bg-brand-50 rounded-lg transition-colors"
                              aria-label="Edit mapping"
                            >
                              <PencilIcon className="h-4 w-4" />
                            </button>
                            <button
                              onClick={() => handleDelete(m.id)}
                              className="p-1.5 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                              aria-label="Delete mapping"
                            >
                              <TrashIcon className="h-4 w-4" />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
