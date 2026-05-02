import { api } from '@/lib/api'

export interface CalendarProperty {
  id: string
  name: string
  address: string
}

export interface CalendarRoomType {
  id: string
  property_id: string
  name: string
  count: number
}

export interface CalendarAvailability {
  room_type_id: string
  available_count: number
  total_count: number
  booked_count: number
  held_count: number
  date: string
}

export interface BlockDatesInput {
  property_id: string
  room_type_ids: string[]
  start_date: string
  end_date: string
  reason: string
}

export async function fetchCalendarData(
  property_id: string,
  year: number,
  month: number,
): Promise<{
  properties: CalendarProperty[]
  roomTypes: CalendarRoomType[]
  availability: CalendarAvailability[]
}> {
  const startDate = new Date(year, month, 1)
  const endDate = new Date(year, month + 1, 1)

  const start = startDate.toISOString().split('T')[0]
  const end = endDate.toISOString().split('T')[0]

  const [properties, roomTypes, availability] = await Promise.all([
    api.get<CalendarProperty[]>('/properties').then((r) => r.data),
    api.get<CalendarRoomType[]>(`/properties/${property_id}/room-types`).then((r) => r.data),
    api.get<CalendarAvailability[]>('/availability/rooms', {
      params: { property_id, check_in: start, check_out: end },
    }).then((r) => r.data),
  ])

  return { properties, roomTypes, availability }
}

export async function blockDates(input: BlockDatesInput): Promise<void> {
  console.warn('blockDates not implemented yet', input)
  await new Promise((resolve) => setTimeout(resolve, 500))
}
