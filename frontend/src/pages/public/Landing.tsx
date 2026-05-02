import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import SearchBar from '@/components/public/SearchBar'
import { getProperties, type Property } from '@/services/propertyApi'

export default function Landing() {
  const navigate = useNavigate()
  const [properties, setProperties] = useState<Property[]>([])
  const [loading] = useState(false)

  useEffect(() => {
    let cancelled = false
    getProperties()
      .then((data) => {
        if (!cancelled) setProperties(data.filter((p) => p.is_active))
      })
      .catch(() => {
        // ignore
      })
    return () => {
      cancelled = true
    }
  }, [])

  const handleSearch = (params: { location: string; checkIn: string; checkOut: string; guests: number }) => {
    const sp = new URLSearchParams()
    sp.set('location', params.location)
    sp.set('check_in', params.checkIn)
    sp.set('check_out', params.checkOut)
    sp.set('guests', String(params.guests))
    navigate(`/book/search?${sp.toString()}`)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="text-xl font-bold text-brand-600">Brekora</div>
          <div className="flex gap-3">
            <a href="/guest/login" className="text-sm text-gray-600 hover:text-gray-900 font-medium">
              Guest Login
            </a>
          </div>
        </div>
      </header>

      <section className="bg-brand-600 py-16 md:py-24">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <h1 className="text-3xl md:text-5xl font-bold text-white mb-4">
            Book your perfect stay
          </h1>
          <p className="text-brand-100 text-lg mb-8 max-w-xl mx-auto">
            Discover unique properties and experiences across India.
          </p>
          <SearchBar onSearch={handleSearch} loading={loading} />
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-4 py-12">
        <h2 className="text-xl font-bold text-gray-900 mb-6">Featured Properties</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {properties.slice(0, 6).map((property) => (
            <div
              key={property.id}
              className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-md transition-shadow"
            >
              <div className="aspect-[16/10] bg-gray-100 relative">
                {property.photos && property.photos[0] ? (
                  <img
                    src={property.photos[0].url}
                    alt={property.name}
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-gray-400 text-sm">
                    No photo
                  </div>
                )}
              </div>
              <div className="p-4">
                <h3 className="text-base font-semibold text-gray-900">{property.name}</h3>
                <p className="text-sm text-gray-500 mt-1 line-clamp-2">{property.address}</p>
                {property.amenities && property.amenities.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1">
                    {property.amenities.slice(0, 4).map((a) => (
                      <span
                        key={a}
                        className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded"
                      >
                        {a}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
