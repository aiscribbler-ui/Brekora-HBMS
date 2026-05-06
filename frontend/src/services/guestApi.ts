import { api } from '@/lib/api'

export interface GuestProfile {
  id: string
  first_name: string | null
  last_name: string | null
  email: string
  phone: string | null
}

export interface GuestProfileUpdate {
  first_name?: string
  last_name?: string
  phone?: string
  current_password?: string
  new_password?: string
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

export interface GuestSignupRequest {
  first_name: string
  last_name: string
  email: string
  phone?: string
  password: string
}

export interface GuestSignupResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  session_id: string
}

export async function signupGuest(data: GuestSignupRequest): Promise<GuestSignupResponse> {
  const { data: response } = await api.post<GuestSignupResponse>('/guest/signup', data)
  return response
}

export async function fetchGuestProfile(): Promise<GuestProfile> {
  const { data } = await api.get<GuestProfile>('/guest/me')
  return data
}

export async function updateGuestProfile(payload: GuestProfileUpdate): Promise<GuestProfile> {
  const { data } = await api.patch<GuestProfile>('/guest/me', payload)
  return data
}

export async function fetchGuestBookings(): Promise<GuestBooking[]> {
  const { data } = await api.get<GuestBooking[]>('/guest/bookings')
  return data
}
