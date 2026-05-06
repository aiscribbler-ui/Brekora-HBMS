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
  const { data } = await api.get<Property[]>('/properties/')
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
  try {
    const { data } = await api.get<{ items: unknown[] }>('/ota/queue')
    return { count: data.items?.length ?? 0 }
  } catch {
    return { count: 0 }
  }
}

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  try {
    const today = new Date().toISOString().split('T')[0]
    const { data } = await api.get<Array<{
      check_in: string
      check_out: string
      status: string
    }>>('/bookings')

    let arrivals = 0
    let departures = 0
    let inHouse = 0
    let pendingCheckIns = 0

    for (const b of data) {
      if (b.check_in === today) {
        arrivals++
        if (b.status === 'confirmed') pendingCheckIns++
      }
      if (b.check_out === today) departures++
      if (b.check_in <= today && b.check_out > today) inHouse++
    }

    return { arrivals, departures, inHouse, pendingCheckIns }
  } catch {
    return { arrivals: 0, departures: 0, inHouse: 0, pendingCheckIns: 0 }
  }
}

export async function fetchWeekSummary(): Promise<WeekSummaryData> {
  try {
    const today = new Date().toISOString().split('T')[0]
    const weekFromNow = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]

    const properties = await fetchProperties()
    if (properties.length === 0) {
      return { occupancyPercent: 0, adrByProperty: [] }
    }

    const availabilityData = await fetchAvailability({
      property_id: properties[0].id,
      check_in: today,
      check_out: weekFromNow,
    })

    const totalRooms = availabilityData.reduce((sum, d) => sum + d.total_count, 0)
    const availableRooms = availabilityData.reduce((sum, d) => sum + d.available_count, 0)
    const occupancyPercent = totalRooms > 0 ? Math.round(((totalRooms - availableRooms) / totalRooms) * 100) : 0

    return {
      occupancyPercent,
      adrByProperty: properties.map((p) => ({
        propertyId: p.id,
        propertyName: p.name,
        adr: 0,
      })),
    }
  } catch {
    return { occupancyPercent: 0, adrByProperty: [] }
  }
}

export async function fetchOpenTasks(): Promise<OpenTasksData> {
  try {
    // OTA queue review count from alerts
    const { data: alertCounts } = await api.get<Array<{ source_type: string; count: number }>>('/ota/alerts/count')
    const otaQueueReview = alertCounts.reduce((sum, entry) => sum + (entry.count ?? 0), 0)

    // Payment failures and pending refunds from bookings
    const { data: bookings } = await api.get<Array<{ status: string }>>('/bookings/')
    const paymentFailures = bookings.filter((b) => b.status === 'payment_failed').length
    const pendingRefunds = bookings.filter((b) => b.status === 'refund_pending').length

    return { otaQueueReview, paymentFailures, pendingRefunds }
  } catch {
    return { otaQueueReview: 0, paymentFailures: 0, pendingRefunds: 0 }
  }
}
