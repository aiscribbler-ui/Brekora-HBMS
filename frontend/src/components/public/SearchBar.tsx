import { useState } from 'react'

interface SearchBarProps {
  onSearch: (params: { location: string; checkIn: string; checkOut: string; guests: number }) => void
  initialValues?: {
    location?: string
    checkIn?: string
    checkOut?: string
    guests?: number
  }
  loading?: boolean
}

export default function SearchBar({ onSearch, initialValues, loading }: SearchBarProps) {
  const [location, setLocation] = useState(initialValues?.location || '')
  const [checkIn, setCheckIn] = useState(initialValues?.checkIn || '')
  const [checkOut, setCheckOut] = useState(initialValues?.checkOut || '')
  const [guests, setGuests] = useState(initialValues?.guests || 2)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!location || !checkIn || !checkOut) return
    onSearch({ location, checkIn, checkOut, guests })
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="w-full bg-white rounded-xl shadow-lg border border-gray-100 p-4 md:p-6"
    >
      <div className="flex flex-col md:flex-row gap-3 md:gap-4 items-end">
        <div className="w-full md:flex-1">
          <label htmlFor="location" className="block text-xs font-medium text-gray-500 mb-1">
            Location
          </label>
          <input
            id="location"
            type="text"
            placeholder="City or property name"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            className="block w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            required
          />
        </div>
        <div className="w-full md:w-40">
          <label htmlFor="checkIn" className="block text-xs font-medium text-gray-500 mb-1">
            Check-in
          </label>
          <input
            id="checkIn"
            type="date"
            value={checkIn}
            min={new Date().toISOString().split('T')[0]}
            onChange={(e) => setCheckIn(e.target.value)}
            className="block w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            required
          />
        </div>
        <div className="w-full md:w-40">
          <label htmlFor="checkOut" className="block text-xs font-medium text-gray-500 mb-1">
            Check-out
          </label>
          <input
            id="checkOut"
            type="date"
            value={checkOut}
            min={checkIn || new Date().toISOString().split('T')[0]}
            onChange={(e) => setCheckOut(e.target.value)}
            className="block w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            required
          />
        </div>
        <div className="w-full md:w-28">
          <label htmlFor="guests" className="block text-xs font-medium text-gray-500 mb-1">
            Guests
          </label>
          <input
            id="guests"
            type="number"
            min={1}
            max={20}
            value={guests}
            onChange={(e) => setGuests(parseInt(e.target.value) || 1)}
            className="block w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            required
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full md:w-auto py-2.5 px-6 bg-brand-600 text-white font-medium rounded-lg hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm whitespace-nowrap"
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
      </div>
    </form>
  )
}
