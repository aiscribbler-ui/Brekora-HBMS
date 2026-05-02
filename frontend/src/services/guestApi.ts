import { api } from '@/lib/api'

export interface GuestProfile {
  id: string
  firstName: string
  lastName: string
  email: string
  phone?: string
}

export interface GuestBooking {
  id: string
  propertyName: string
  checkIn: string
  checkOut: string
  status: string
}

export async function fetchGuestProfile(): Promise<GuestProfile> {
  // Stub: replace with actual endpoint when available
  const { data } = await api.get<GuestProfile>('/guest/me')
  return data
}

export async function fetchGuestBookings(): Promise<GuestBooking[]> {
  // Stub: replace with actual endpoint when available
  const { data } = await api.get<GuestBooking[]>('/guest/bookings')
  return data
}

export async function updateGuestProfile(payload: Partial<GuestProfile>): Promise<GuestProfile> {
  // Stub: replace with actual endpoint when available
  const { data } = await api.patch<GuestProfile>('/guest/me', payload)
  return data
}
