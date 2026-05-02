import axios from 'axios'

const publicApi = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

export interface PropertySnippet {
  id: string
  name: string
  address?: string | null
  photos?: { url: string; caption?: string }[] | null
  amenities?: string[] | null
}

export interface PriceBreakdown {
  subtotal: number
  discount_amount: number
  taxable_amount: number
  tax_amount: number
  gst_rate: number
  channel_markup_amount: number
  total_amount: number
  currency: string
  breakdown_per_night: Record<string, unknown>[]
}

export interface SearchRequest {
  location: string
  check_in: string
  check_out: string
  guests: number
  promo_code?: string | null
}

export interface SearchResultItem {
  type: 'room' | 'package'
  id: string
  name: string
  photos?: { url: string; caption?: string }[] | null
  description?: string | null
  available: boolean
  price_breakdown: PriceBreakdown
  property: PropertySnippet
}

export interface SearchResponse {
  results: SearchResultItem[]
}

export interface AvailabilityRequest {
  property_id: string
  room_type_id?: string
  check_in: string
  check_out: string
}

export interface RoomAvailabilityNight {
  date: string
  available_count: number
  total_count: number
  booked_count: number
  held_count: number
}

export interface RoomAvailabilityResponse {
  nights: RoomAvailabilityNight[]
}

export interface BookingInitRequest {
  property_id: string
  item_type: 'room' | 'package'
  item_id: string
  check_in: string
  check_out: string
  guests: number
  add_on_selections?: { add_on_id: string; date: string; quantity: number; slot_time?: string | null }[] | null
  rate_plan_code?: string | null
  promo_code?: string | null
  channel_source?: string | null
  guest_id?: string | null
  idempotency_key?: string | null
  notes?: string | null
}

export interface BookingInitResponse {
  booking_id: string
  hold_id: string
  hold_expires_at: string
  amount_breakdown: PriceBreakdown
}

export interface OrderCreateResponse {
  order_id: string
  amount: number
  currency: string
  status: string
}

export interface Property {
  id: string
  name: string
  address: string
  photos?: { url: string; caption?: string }[] | null
  amenities?: string[] | null
  default_check_in_time?: string | null
  default_check_out_time?: string | null
  is_active: boolean
}

export interface RoomType {
  id: string
  property_id: string
  name: string
  description?: string | null
  count: number
  base_capacity: number
  max_capacity: number
  default_rate: string
  photos?: { url: string; caption?: string }[] | null
  is_active: boolean
}

export interface PackageItem {
  id: string
  property_id: string
  name: string
  description?: string | null
  status: string
  base_price: string
  max_occupancy?: number | null
  is_active: boolean
}

export async function searchProperties(query: string): Promise<Property[]> {
  const { data } = await publicApi.get<Property[]>('/properties', { params: { q: query } })
  return data
}

export async function getPropertyDetails(id: string): Promise<Property> {
  const { data } = await publicApi.get<Property>(`/properties/${id}`)
  return data
}

export async function searchAvailability(data: SearchRequest): Promise<SearchResponse> {
  const { data: responseData } = await publicApi.post<SearchResponse>('/search', data)
  return responseData
}

export async function getRoomAvailability(params: AvailabilityRequest): Promise<RoomAvailabilityResponse> {
  const { data } = await publicApi.get<RoomAvailabilityResponse>('/availability/rooms', { params })
  return data
}

export async function initBooking(data: BookingInitRequest): Promise<BookingInitResponse> {
  const { data: responseData } = await publicApi.post<BookingInitResponse>('/bookings/init', data)
  return responseData
}

export async function createOrder(bookingId: string): Promise<OrderCreateResponse> {
  const { data } = await publicApi.post<OrderCreateResponse>('/payments/create-order', { booking_id: bookingId })
  return data
}

export async function retryPayment(bookingId: string): Promise<OrderCreateResponse> {
  const { data } = await publicApi.post<OrderCreateResponse>('/payments/retry', { booking_id: bookingId })
  return data
}

export function isAxiosError<T = unknown>(error: unknown): error is import('axios').AxiosError<T> {
  return axios.isAxiosError(error)
}
