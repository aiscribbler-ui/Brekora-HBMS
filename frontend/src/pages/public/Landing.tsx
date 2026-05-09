import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { MapPin, Sparkles, Wifi, ShieldCheck } from 'lucide-react'
import SearchBar from '@/components/public/SearchBar'
import { getProperties, type Property } from '@/services/propertyApi'
import {
  ShieldCheckIcon,
  StarIcon,
  MapPinIcon,
  WifiIcon,
} from '@heroicons/react/24/outline'

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
    <div className="min-h-screen bg-white">
      {/* Sticky Header */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-sm">
              <span className="text-white font-bold text-sm">B</span>
            </div>
            <span className="text-xl font-bold bg-gradient-to-r from-brand-600 to-brand-800 bg-clip-text text-transparent">
              Brekora
            </span>
          </div>
          <a
            href="/guest/login"
            className="text-sm text-gray-600 hover:text-brand-600 font-medium transition-colors"
          >
            Guest Login
          </a>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-to-br from-brand-600 via-brand-700 to-brand-900 py-20 md:py-28">
        {/* Floating blobs */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-24 -left-24 w-72 h-72 bg-white/10 rounded-full blur-3xl animate-pulse" />
          <div className="absolute top-1/2 -right-24 w-96 h-96 bg-brand-400/20 rounded-full blur-3xl" />
          <div className="absolute bottom-0 left-1/3 w-64 h-64 bg-white/5 rounded-full blur-2xl" />
        </div>

        <div className="relative max-w-4xl mx-auto px-4 text-center">
          <h1 className="text-4xl md:text-6xl font-bold text-white mb-4 tracking-tight">
            Book your perfect stay
          </h1>
          <p className="text-brand-100 text-lg mb-10 max-w-xl mx-auto">
            Discover unique properties and curated experiences across India.
          </p>

          {/* Floating search card */}
          <div className="bg-white rounded-2xl shadow-xl p-4 md:p-6 transform hover:scale-[1.01] transition-transform">
            <SearchBar onSearch={handleSearch} loading={loading} />
          </div>
        </div>
      </section>

      {/* Trust badges */}
      <section className="border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 py-8">
          <div className="flex flex-wrap items-center justify-center gap-6 md:gap-10">
            {[
              { icon: ShieldCheckIcon, label: 'Secure Payments' },
              { icon: StarIcon, label: 'Curated Stays' },
              { icon: MapPinIcon, label: 'Prime Locations' },
              { icon: WifiIcon, label: 'Modern Amenities' },
            ].map(({ icon: Icon, label }) => (
              <div key={label} className="flex items-center gap-2 text-gray-500">
                <Icon className="h-5 w-5 text-brand-500" aria-hidden="true" />
                <span className="text-sm font-medium">{label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Properties */}
      <section className="max-w-7xl mx-auto px-4 py-14">
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-2xl font-bold text-gray-900">Featured Properties</h2>
          <span className="text-sm text-gray-500">
            {properties.length} property{properties.length === 1 ? 'y' : 'ies'}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
          {properties.slice(0, 6).map((property) => (
            <div
              key={property.id}
              className="group bg-white rounded-2xl border border-gray-100 overflow-hidden hover:shadow-xl hover:-translate-y-1 transition-all duration-300"
            >
              <div className="aspect-[16/10] bg-gray-100 relative overflow-hidden">
                {property.photos && property.photos[0] ? (
                  <img
                    src={property.photos[0].url}
                    alt={property.name}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                    loading="lazy"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-gray-400 text-sm">
                    <MapPinIcon className="h-8 w-8 mb-1" />
                    <span>No photo</span>
                  </div>
                )}
                <div className="absolute top-3 left-3">
                  <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-white/90 text-gray-800 backdrop-blur-sm shadow-sm">
                    {property.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </div>
              <div className="p-5">
                <h3 className="text-base font-semibold text-gray-900 group-hover:text-brand-700 transition-colors">
                  {property.name}
                </h3>
                <p className="text-sm text-gray-500 mt-1 line-clamp-2">{property.address}</p>
                {property.amenities && property.amenities.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {property.amenities.slice(0, 4).map((a) => (
                      <span
                        key={a}
                        className="px-2.5 py-0.5 bg-brand-50 text-brand-700 text-xs rounded-full font-medium"
                      >
                        {a}
                      </span>
                    ))}
                  </div>
                )}
                <button
                  onClick={() => {
                    const today = new Date()
                    const tomorrow = new Date(today)
                    tomorrow.setDate(today.getDate() + 1)
                    const sp = new URLSearchParams()
                    sp.set('location', property.city || property.name)
                    sp.set('check_in', today.toISOString().split('T')[0])
                    sp.set('check_out', tomorrow.toISOString().split('T')[0])
                    sp.set('guests', '2')
                    navigate(`/book/search?${sp.toString()}`)
                  }}
                  className="mt-4 w-full py-2 px-4 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
                >
                  Book Now
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-100 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 py-10 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center">
              <span className="text-white font-bold text-xs">B</span>
            </div>
            <span className="text-sm font-semibold text-gray-700">Brekora</span>
          </div>
          <p className="text-xs text-gray-400">
            © {new Date().getFullYear()} Brekora Hospitality. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  )
}
