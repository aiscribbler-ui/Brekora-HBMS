import { api } from '@/lib/api'

export type OtaSource = 'airbnb' | 'mmt' | 'goibibo' | 'other'
export type QueueStatus = 'pending' | 'confirmed' | 'rejected' | 'edited'

export interface ParsedBooking {
  id: string
  property_id: string
  source_type: OtaSource
  status: QueueStatus
  guest_name: string | null
  guest_email: string | null
  guest_phone: string | null
  check_in: string | null
  check_out: string | null
  num_guests: number | null
  room_type: string | null
  ota_reference: string | null
  confidence_score: number
  raw_email_id: string | null
  parsed_data: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface QueueListResponse {
  items: ParsedBooking[]
  total: number
  page: number
  page_size: number
}

export interface QueueFilters {
  source_type?: OtaSource
  status?: QueueStatus
  date_from?: string
  date_to?: string
  page?: number
  page_size?: number
}

export interface ConfirmPayload {
  room_type_id?: string
  mapping_id?: string
}

export interface EditPayload {
  parsed_data: Record<string, unknown>
  guest_name?: string
  check_in?: string
  check_out?: string
  guest_email?: string
  guest_phone?: string
  num_guests?: number
  room_type?: string
  ota_reference?: string
}

export interface RejectPayload {
  rejection_reason: string
}

export interface OtaMapping {
  id: string
  property_id: string
  ota_source: OtaSource
  ota_listing_id: string
  room_type_id: string
  is_active: boolean
}

export async function getOtaQueue(filters?: QueueFilters): Promise<QueueListResponse> {
  const { data } = await api.get<QueueListResponse>('/ota/queue', { params: filters })
  return data
}

export async function getOtaQueueItem(id: string): Promise<ParsedBooking> {
  const { data } = await api.get<ParsedBooking>(`/ota/queue/${id}`)
  return data
}

export async function confirmOtaQueueItem(id: string, payload: ConfirmPayload): Promise<ParsedBooking> {
  const { data } = await api.post<ParsedBooking>(`/ota/queue/${id}/confirm`, payload)
  return data
}

export async function editOtaQueueItem(id: string, payload: EditPayload): Promise<ParsedBooking> {
  const { data } = await api.post<ParsedBooking>(`/ota/queue/${id}/edit`, payload)
  return data
}

export async function rejectOtaQueueItem(id: string, payload: RejectPayload): Promise<ParsedBooking> {
  const { data } = await api.post<ParsedBooking>(`/ota/queue/${id}/reject`, payload)
  return data
}

export async function getOtaMappings(propertyId: string): Promise<OtaMapping[]> {
  const { data } = await api.get<OtaMapping[]>(`/properties/${propertyId}/ota-mappings`)
  return data
}
