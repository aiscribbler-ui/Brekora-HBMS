import { api } from '@/lib/api'

export interface Property {
  id: string
  name: string
  address: string
  status: string
}

export interface RoomType {
  id: string
  name: string
  property_id: string
  count: number
  base_rate: number
}

export interface AvailabilityParams {
  property_id?: string
  room_type_id?: string
  check_in: string
  check_out: string
}

export interface AvailabilityResponse {
  room_type_id: string
  available_count: number
  total_count: number
  date: string
}

export interface DashboardSummary {
  arrivals: number
  departures: number
  inHouse: number
  pendingCheckIns: number
}

export interface WeekSummaryData {
  occupancyPercent: number
  adrByProperty: { propertyId: string; propertyName: string; adr: number }[]
}

export interface OpenTasksData {
  otaQueueReview: number
  paymentFailures: number
  pendingRefunds: number
}

export async function fetchProperties(): Promise<Property[]> {
  const { data } = await api.get<Property[]>('/properties')
  return data
}

export async function fetchRoomTypes(propertyId: string): Promise<RoomType[]> {
  const { data } = await api.get<RoomType[]>(`/properties/${propertyId}/room-types`)
  return data
}

export async function fetchAvailability(params: AvailabilityParams): Promise<AvailabilityResponse[]> {
  const { data } = await api.get<AvailabilityResponse[]>('/availability/rooms', { params })
  return data
}

export async function fetchRawEmailQueue(): Promise<{ count: number }> {
  // Stub: raw email/OTA endpoints exist but parsers are still being built
  // Return mock data until the queue API is ready (C-006)
  return { count: 0 }
}

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  // Stub: Booking API does not exist yet (B-007 working on it)
  // Return mock data until booking endpoints are available
  return {
    arrivals: 0,
    departures: 0,
    inHouse: 0,
    pendingCheckIns: 0,
  }
}

export async function fetchWeekSummary(): Promise<WeekSummaryData> {
  // Stub: calculate from availability API when possible
  // For now return mock data
  return {
    occupancyPercent: 0,
    adrByProperty: [],
  }
}

export async function fetchOpenTasks(): Promise<OpenTasksData> {
  // Stub: payment and refund APIs not ready yet
  return {
    otaQueueReview: 0,
    paymentFailures: 0,
    pendingRefunds: 0,
  }
}
