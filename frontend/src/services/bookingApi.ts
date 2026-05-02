import { api, isAxiosError } from '@/lib/api'
import type { AxiosError } from 'axios'

export interface AddOnSelection {
  add_on_id: string
  date: string
  quantity: number
  slot_time?: string | null
}

export interface BookingInitRequest {
  property_id: string
  item_type: 'room' | 'package'
  item_id: string
  check_in: string
  check_out: string
  guests: number
  add_on_selections?: AddOnSelection[] | null
  rate_plan_code?: string | null
  promo_code?: string | null
  channel_source?: string | null
  guest_id?: string | null
  idempotency_key?: string | null
  notes?: string | null
}

export interface AmountBreakdown {
  subtotal: number
  discount_amount: number
  taxable_amount: number
  tax_amount: number
  channel_markup_amount: number
  total_amount: number
  currency: string
  breakdown_per_night: Record<string, unknown>[]
}

export interface BookingInitResponse {
  booking_id: string
  hold_id: string
  hold_expires_at: string
  amount_breakdown: AmountBreakdown
}

export interface OrderCreateResponse {
  order_id: string
  amount: number
  currency: string
  status: string
}

export interface ConflictAlternative {
  type: 'room' | 'package'
  id: string
  name: string
  check_in: string
  check_out: string
  price_per_night: number
  available_count: number
}

export interface ConflictErrorData {
  detail: string
  alternatives?: ConflictAlternative[]
}

export async function initBooking(data: BookingInitRequest): Promise<BookingInitResponse> {
  const { data: responseData } = await api.post<BookingInitResponse>('/bookings/init', data)
  return responseData
}

export async function createOrder(bookingId: string): Promise<OrderCreateResponse> {
  const { data } = await api.post<OrderCreateResponse>('/payments/create-order', { booking_id: bookingId })
  return data
}

export async function retryPayment(bookingId: string): Promise<OrderCreateResponse> {
  const { data } = await api.post<OrderCreateResponse>('/payments/retry', { booking_id: bookingId })
  return data
}

export function extractConflictAlternatives(error: unknown): ConflictAlternative[] | undefined {
  if (isAxiosError<ConflictErrorData>(error)) {
    return error.response?.data?.alternatives
  }
  return undefined
}

export interface BookingLineItemRecord {
  id: string
  booking_id: string
  item_type: string
  item_id: string
  quantity: number
  unit_price: number
  nights: number
  total_price: number
  created_at: string
  updated_at: string
}

export interface ModificationLogEntry {
  timestamp: string
  actor_user_id: string | null
  changes: Record<string, { old: unknown; new: unknown }>
  reason: string
}

export interface GuestDetails {
  name?: string
  email?: string
  phone?: string
  id_number?: string
  guests?: number
}

export interface Booking {
  id: string
  org_id: string
  booking_type: string
  source_type: string
  source_reference: string | null
  property_id: string
  guest_id: string | null
  check_in: string
  check_out: string
  status: string
  line_items: Array<Record<string, unknown>> | null
  gross_amount: number
  discount_amount: number
  tax_amount: number
  total_amount: number
  currency: string
  cancellation_policy_snapshot: Record<string, unknown> | null
  partner_attribution_id: string | null
  payment_state: string | null
  idempotency_key: string | null
  notes: string | null
  created_at: string
  updated_at: string
  cancelled_at: string | null
  cancellation_reason: string | null
  modification_log: ModificationLogEntry[] | null
  line_item_records: BookingLineItemRecord[]
  guest?: GuestDetails | null
}

export interface BookingModificationRequest {
  check_in?: string | null
  check_out?: string | null
  room_type_id?: string | null
  add_ons?: AddOnSelection[] | null
  guest_details?: Record<string, unknown> | null
  reason?: string | null
  override_24h?: boolean
}

export interface BookingModificationResponse extends Booking {
  payment_difference: number
  new_total: number
  razorpay_order: Record<string, unknown> | null
  refund_amount: number | null
}

export async function getBooking(id: string): Promise<Booking> {
  const { data } = await api.get<Booking>(`/bookings/${id}`)
  return data
}

export async function modifyBooking(
  id: string,
  data: BookingModificationRequest,
): Promise<BookingModificationResponse> {
  const { data: responseData } = await api.patch<BookingModificationResponse>(`/bookings/${id}/modify`, data)
  return responseData
}

export async function cancelBooking(id: string, reason: string): Promise<Booking> {
  const { data } = await api.patch<Booking>(`/bookings/${id}`, { status: 'cancelled', cancellation_reason: reason })
  return data
}

export function isConflictError(error: unknown): error is AxiosError<ConflictErrorData> {
  return isAxiosError<ConflictErrorData>(error) && error.response?.status === 409
}
