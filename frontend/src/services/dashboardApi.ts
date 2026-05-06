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

interface BookingRecord {
  id: string
  property_id?: string
  check_in: string
  check_out: string
  status: string
  total_amount?: number
}

interface BookingListResponse {
  items?: BookingRecord[]
  total?: number
}

interface BookingSummaryResponse {
  arrivals: number
  departures: number
  in_house: number
  pending_check_ins: number
  payment_failures: number
  pending_refunds: number
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

async function fetchBookings(params?: Record<string, string>): Promise<BookingRecord[]> {
  try {
    const { data } = await api.get<BookingRecord[] | BookingListResponse>('/bookings', { params })
    if (Array.isArray(data)) return data
    return data.items ?? []
  } catch {
    return []
  }
}

async function fetchBookingsSummary(): Promise<BookingSummaryResponse | null> {
  try {
    const { data } = await api.get<BookingSummaryResponse>('/bookings/summary')
    return data
  } catch {
    return null
  }
}

export async function fetchRawEmailQueue(): Promise<{ count: number }> {
  try {
    const { data } = await api.get<{ items?: unknown[]; total?: number }>('/ota/queue')
    const count = Array.isArray(data?.items) ? data.items.length : (data?.total ?? 0)
    return { count }
  } catch {
    return { count: 0 }
  }
}

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  const summary = await fetchBookingsSummary()
  if (summary) {
    return {
      arrivals: summary.arrivals,
      departures: summary.departures,
      inHouse: summary.in_house,
      pendingCheckIns: summary.pending_check_ins,
    }
  }

  // Fallback: derive locally if /bookings/summary is unavailable.
  const today = new Date().toISOString().split('T')[0]
  const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString().split('T')[0]
  const bookings = await fetchBookings({ overlaps_from: today, overlaps_to: tomorrow })

  let arrivals = 0
  let departures = 0
  let inHouse = 0
  let pendingCheckIns = 0

  for (const b of bookings) {
    const checkIn = (b.check_in || '').slice(0, 10)
    const checkOut = (b.check_out || '').slice(0, 10)
    const status = (b.status || '').toLowerCase()

    if (status === 'cancelled') continue

    if (checkIn === today) arrivals += 1
    if (checkOut === today) departures += 1
    if (checkIn <= today && checkOut > today) inHouse += 1
    if (checkIn === today && status === 'confirmed') pendingCheckIns += 1
  }

  return { arrivals, departures, inHouse, pendingCheckIns }
}

export async function fetchWeekSummary(): Promise<WeekSummaryData> {
  return {
    occupancyPercent: 0,
    adrByProperty: [],
  }
}

export async function fetchOpenTasks(): Promise<OpenTasksData> {
  let otaQueueReview = 0
  try {
    const { data } = await api.get<Record<string, number> | { total?: number; counts?: Record<string, number> }>(
      '/ota/alerts/count',
    )
    if (typeof data === 'object' && data !== null) {
      if ('counts' in data && data.counts) {
        otaQueueReview = Object.values(data.counts).reduce((sum, n) => sum + (Number(n) || 0), 0)
      } else if ('total' in data && typeof data.total === 'number') {
        otaQueueReview = data.total
      } else {
        otaQueueReview = Object.values(data as Record<string, number>).reduce(
          (sum, n) => sum + (Number(n) || 0),
          0,
        )
      }
    }
  } catch {
    otaQueueReview = 0
  }

  const summary = await fetchBookingsSummary()
  if (summary) {
    return {
      otaQueueReview,
      paymentFailures: summary.payment_failures,
      pendingRefunds: summary.pending_refunds,
    }
  }

  // Fallback to scanning the list endpoint.
  const bookings = await fetchBookings({ status: 'payment_failed' })
  return {
    otaQueueReview,
    paymentFailures: bookings.length,
    pendingRefunds: 0,
  }
}
