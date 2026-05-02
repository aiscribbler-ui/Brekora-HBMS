import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PlusIcon, MagnifyingGlassIcon, BuildingOfficeIcon } from '@heroicons/react/24/outline'
import { getProperties, type Property } from '@/services/propertyApi'
import { isAxiosError } from '@/lib/api'

export default function PropertyList() {
  const navigate = useNavigate()
  const [properties, setProperties] = useState<Property[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    getProperties()
      .then((data) => {
        if (!cancelled) setProperties(data)
      })
      .catch((err) => {
        if (!cancelled) {
          if (isAxiosError(err) && err.response?.data?.detail) {
            setError(err.response.data.detail)
          } else {
            setError('Failed to load properties.')
          }
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return properties
    return properties.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.address.toLowerCase().includes(q),
    )
  }, [properties, search])

  const activeCount = useMemo(() => properties.filter((p) => p.is_active && !p.is_archived).length, [properties])

  return (
    <div className="max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Properties</h1>
          <p className="text-sm text-gray-500 mt-1">{activeCount} active property{activeCount !== 1 ? 'ies' : 'y'}</p>
        </div>
        <button
          onClick={() => navigate('/properties/new')}
          className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-md hover:bg-brand-700 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
          aria-label="Add property"
        >
          <PlusIcon className="h-4 w-4" />
          Add Property
        </button>
      </div>

      <div className="mb-4 relative">
        <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" aria-hidden="true" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name or address..."
          aria-label="Search properties by name or address"
          className="w-full sm:w-80 pl-9 pr-3 py-2 rounded-md border border-gray-300 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded border border-red-200 text-sm" role="alert">
          {error}
        </div>
      )}

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-16 bg-gray-100 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-lg border border-gray-200">
          <BuildingOfficeIcon className="mx-auto h-10 w-10 text-gray-300" />
          <p className="mt-3 text-sm text-gray-500">No properties found.</p>
          {search && (
            <button
              onClick={() => setSearch('')}
              className="mt-2 text-sm text-brand-600 hover:underline"
            >
              Clear search
            </button>
          )}
        </div>
      ) : (
        <>
          {/* Desktop table */}
          <div className="hidden md:block bg-white rounded-lg border border-gray-200 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Address</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Room Count</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filtered.map((property) => (
                  <tr
                    key={property.id}
                    onClick={() => navigate(`/properties/${property.id}`)}
                    className="hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{property.name}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 max-w-xs truncate">{property.address}</td>
                    <td className="px-4 py-3">
                      {property.is_archived ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                          Archived
                        </span>
                      ) : property.is_active ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                          Inactive
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">-</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile cards */}
          <div className="md:hidden space-y-3">
            {filtered.map((property) => (
              <button
                key={property.id}
                onClick={() => navigate(`/properties/${property.id}`)}
                className="w-full text-left bg-white rounded-lg border border-gray-200 p-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-gray-900">{property.name}</h3>
                  {property.is_archived ? (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                      Archived
                    </span>
                  ) : property.is_active ? (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                      Active
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                      Inactive
                    </span>
                  )}
                </div>
                <p className="mt-1 text-xs text-gray-500 line-clamp-2">{property.address}</p>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
