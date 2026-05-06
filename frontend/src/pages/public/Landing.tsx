import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { MapPin, Sparkles, Wifi, ShieldCheck } from 'lucide-react'
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
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white/80 backdrop-blur border-b border-gray-200 sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center text-white font-bold shadow-sm">
              B
            </div>
            <span className="text-xl font-bold text-gray-900">Brekora</span>
          </div>
          <div className="flex gap-3 items-center">
            <a
              href="/guest/login"
              className="text-sm text-gray-600 hover:text-gray-900 font-medium px-3 py-1.5 rounded-md hover:bg-gray-100 transition-colors"
            >
              Guest Login
            </a>
            <a
              href="/guest/signup"
              className="text-sm bg-brand-600 hover:bg-brand-700 text-white font-medium px-4 py-1.5 rounded-md shadow-sm transition-colors"
            >
              Sign Up
            </a>
          </div>
        </div>
      </header>

      <section className="relative bg-gradient-to-br from-brand-600 to-brand-800 py-20 md:py-28 overflow-hidden">
        <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
          <div className="absolute -top-24 -left-24 w-72 h-72 bg-brand-400/30 rounded-full blur-3xl animate-float-slow" />
          <div className="absolute top-1/3 -right-16 w-80 h-80 bg-brand-300/20 rounded-full blur-3xl animate-float-medium" />
          <div className="absolute -bottom-24 left-1/3 w-96 h-96 bg-brand-500/25 rounded-full blur-3xl animate-float-slow" />
          <div
            className="absolute inset-0 opacity-[0.07]"
            style={{
              backgroundImage:
                'radial-gradient(circle at 1px 1px, white 1px, transparent 0)',
              backgroundSize: '32px 32px',
            }}
          />
        </div>

        <div className="relative max-w-5xl mx-auto px-4 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 backdrop-blur text-brand-100 text-xs font-medium mb-5 border border-white/20">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Curated stays across India</span>
          </div>
          <h1 className="text-4xl md:text-6xl font-bold text-white mb-4 tracking-tight">
            Book your perfect stay
          </h1>
          <p className="text-brand-100 text-lg md:text-xl mb-10 max-w-2xl mx-auto">
            Discover unique properties and experiences — handpicked for memorable getaways.
          </p>
          <div className="max-w-4xl mx-auto">
            <SearchBar onSearch={handleSearch} loading={loading} />
          </div>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-4 py-14 w-full flex-1">
        <div className="flex items-end justify-between mb-8">
          <div>
            <h2 className="text-2xl md:text-3xl font-bold text-gray-900">Featured Properties</h2>
            <p className="text-sm text-gray-500 mt-1">Hand-picked stays loved by guests.</p>
          </div>
        </div>

        {properties.length === 0 ? (
          <div className="text-center py-16 rounded-2xl border border-dashed border-gray-200 bg-white">
            <Sparkles className="w-10 h-10 text-gray-300 mx-auto mb-2" />
            <p className="text-sm text-gray-500">No properties available yet — check back soon.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {properties.slice(0, 6).map((property) => (
              <article
                key={property.id}
                className="group bg-white rounded-2xl border border-gray-100 overflow-hidden shadow-sm hover:-translate-y-1 hover:shadow-xl transition-all duration-200 flex flex-col"
              >
                <div className="aspect-[4/3] bg-gradient-to-br from-gray-100 to-gray-200 relative overflow-hidden">
                  {property.photos && property.photos[0] ? (
                    <img
                      src={property.photos[0].url}
                      alt={property.name}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      loading="lazy"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-400">
                      <Sparkles className="w-8 h-8" />
                    </div>
                  )}
                  <div className="absolute top-3 right-3 px-2.5 py-1 rounded-full bg-white/95 backdrop-blur text-xs font-medium text-brand-700 shadow-sm">
                    Featured
                  </div>
                </div>
                <div className="p-5 flex flex-col flex-1">
                  <h3 className="text-lg font-semibold text-gray-900 group-hover:text-brand-700 transition-colors">
                    {property.name}
                  </h3>
                  <p className="text-sm text-gray-500 mt-1 flex items-start gap-1.5 line-clamp-2">
                    <MapPin className="w-4 h-4 mt-0.5 flex-shrink-0 text-gray-400" />
                    <span>{property.address}</span>
                  </p>
                  {property.amenities && property.amenities.length > 0 && (
                    <div className="mt-4 flex flex-wrap gap-1.5">
                      {property.amenities.slice(0, 4).map((a) => (
                        <span
                          key={a}
                          className="inline-flex items-center gap-1 px-2.5 py-1 bg-brand-50 text-brand-700 text-xs font-medium rounded-full border border-brand-100"
                        >
                          {a}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="max-w-7xl mx-auto px-4 pb-14 w-full grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { icon: ShieldCheck, title: 'Verified properties', desc: 'Every listing reviewed and trust-checked.' },
          { icon: Wifi, title: 'Modern amenities', desc: 'Wi-Fi, comfort, and care included.' },
          { icon: Sparkles, title: 'Best price guarantee', desc: 'Direct rates with no hidden fees.' },
        ].map(({ icon: Icon, title, desc }) => (
          <div
            key={title}
            className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm flex items-start gap-3"
          >
            <div className="w-10 h-10 rounded-lg bg-brand-50 text-brand-600 flex items-center justify-center flex-shrink-0">
              <Icon className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">{title}</h3>
              <p className="text-sm text-gray-500 mt-0.5">{desc}</p>
            </div>
          </div>
        ))}
      </section>

      <footer className="border-t border-gray-200 bg-white">
        <div className="max-w-7xl mx-auto px-4 py-6 flex flex-col md:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-md bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center text-white text-xs font-bold">
              B
            </div>
            <span className="text-sm font-semibold text-gray-700">Brekora</span>
            <span className="text-xs text-gray-400">— Hospitality, simplified.</span>
          </div>
          <p className="text-xs text-gray-400">
            © {new Date().getFullYear()} Brekora. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  )
}
