import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import SearchBar from '@/components/public/SearchBar'
import RoomCard from '@/components/public/RoomCard'
import PackageCard from '@/components/public/PackageCard'
import { searchAvailability, type SearchResultItem } from '@/services/publicApi'
import { isAxiosError } from '@/lib/api'

export default function SearchResults() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const location = searchParams.get('location') || ''
  const checkIn = searchParams.get('check_in') || ''
  const checkOut = searchParams.get('check_out') || ''
  const guestsParam = searchParams.get('guests') || '2'
  const guests = parseInt(guestsParam) || 2

  const [results, setResults] = useState<SearchResultItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!location || !checkIn || !checkOut) return
    let cancelled = false
    setLoading(true)
    setError(null)
    searchAvailability({
      location,
      check_in: checkIn,
      check_out: checkOut,
      guests,
    })
      .then((data) => {
        if (!cancelled) setResults(data.results)
      })
      .catch((err) => {
        if (!cancelled) {
          if (isAxiosError<{ detail?: string }>(err) && err.response?.data?.detail) {
            setError(err.response.data.detail)
          } else {
            setError('Search failed. Please try again.')
          }
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [location, checkIn, checkOut, guests])

  const handleSearch = (params: { location: string; checkIn: string; checkOut: string; guests: number }) => {
    const sp = new URLSearchParams()
    sp.set('location', params.location)
    sp.set('check_in', params.checkIn)
    sp.set('check_out', params.checkOut)
    sp.set('guests', String(params.guests))
    navigate(`/book/search?${sp.toString()}`, { replace: true })
  }

  const handleSelect = (item: SearchResultItem) => {
    const sp = new URLSearchParams(searchParams)
    sp.set('item_id', item.id)
    sp.set('item_type', item.type)
    sp.set('property_id', item.property.id)
    navigate(`/book/flow?${sp.toString()}`)
  }

  const rooms = results.filter((r) => r.type === 'room')
  const packages = results.filter((r) => r.type === 'package')

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <a href="/book" className="text-xl font-bold text-brand-600">Brekora</a>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6">
        <SearchBar
          onSearch={handleSearch}
          loading={loading}
          initialValues={{ location, checkIn, checkOut, guests }}
        />
      </div>

      <div className="max-w-7xl mx-auto px-4 pb-12">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4 font-display">Search Results</h1>

        {error && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded border border-red-200 dark:border-red-800 text-sm">
            {error}
          </div>
        )}

        {loading && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
                <div className="aspect-[16/10] bg-gray-100 dark:bg-gray-700 animate-pulse" />
                <div className="p-4 space-y-3">
                  <div className="h-4 bg-gray-100 dark:bg-gray-700 rounded w-3/4 animate-pulse" />
                  <div className="h-3 bg-gray-100 dark:bg-gray-700 rounded w-1/2 animate-pulse" />
                  <div className="h-8 bg-gray-100 dark:bg-gray-700 rounded w-1/3 animate-pulse" />
                </div>
              </div>
            ))}
          </div>
        )}

        {!loading && results.length === 0 && !error && (
          <div className="text-center py-16">
            <p className="text-gray-500 dark:text-gray-400">No results found. Try different dates or location.</p>
          </div>
        )}

        {!loading && rooms.length > 0 && (
          <div className="mb-8">
            <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-4">Rooms</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {rooms.map((item) => (
                <RoomCard key={item.id} item={item} onSelect={() => handleSelect(item)} />
              ))}
            </div>
          </div>
        )}

        {!loading && packages.length > 0 && (
          <div>
            <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-4">Packages</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {packages.map((item) => (
                <PackageCard key={item.id} item={item} onSelect={() => handleSelect(item)} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
