import { api } from '@/lib/api'

export interface GuestProfile {
  id: string
  first_name: string | null
  last_name: string | null
  email: string
  phone: string | null
}

export interface GuestBooking {
  id: string
  property_id: string
  check_in: string
  check_out: string
  status: string
  total_amount: number
  currency: string
}

export async function fetchGuestProfile(): Promise<GuestProfile> {
  const { data } = await api.get<GuestProfile>('/guest/me')
  return data
}

export async function fetchGuestBookings(): Promise<GuestBooking[]> {
  const { data } = await api.get<GuestBooking[]>('/guest/bookings')
  return data
}

export async function updateGuestProfile(payload: Partial<GuestProfile>): Promise<GuestProfile> {
  const { data } = await api.patch<GuestProfile>('/guest/me', payload)
  return data
}
