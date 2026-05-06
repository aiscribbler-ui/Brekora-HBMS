import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  fetchCalendarData,
  fetchCalendarProperties,
  blockDates,
  type CalendarProperty,
  type CalendarRoomType,
  type CalendarAvailability,
  type BlockDatesInput,
} from '@/services/calendarApi'
import { isAxiosError } from '@/lib/api'

interface CalendarState {
  properties: CalendarProperty[]
  roomTypes: CalendarRoomType[]
  availability: CalendarAvailability[]
  isLoading: boolean
  error: string | null
}

const initialState: CalendarState = {
  properties: [],
  roomTypes: [],
  availability: [],
  isLoading: true,
  error: null,
}

export function useCalendar() {
  const [currentMonth, setCurrentMonth] = useState<Date>(new Date())
  const [selectedPropertyId, setSelectedPropertyId] = useState<string>('')
  const [state, setState] = useState<CalendarState>(initialState)

  // Always load properties so the dropdown is populated, regardless of selection.
  useEffect(() => {
    let cancelled = false
    fetchCalendarProperties()
      .then((properties) => {
        if (cancelled) return
        setState((prev) => ({ ...prev, properties }))
        if (properties.length > 0) {
          setSelectedPropertyId((prev) => prev || properties[0].id)
        } else {
          setState((prev) => ({ ...prev, isLoading: false }))
        }
      })
      .catch((err) => {
        if (cancelled) return
        let message = 'Failed to load properties.'
        if (isAxiosError(err) && err.response?.data?.detail) {
          message = err.response.data.detail
        }
        setState((prev) => ({ ...prev, isLoading: false, error: message }))
      })
    return () => {
      cancelled = true
    }
  }, [])

  const loadCalendar = useCallback(async () => {
    if (!selectedPropertyId) return

    setState((prev) => ({ ...prev, isLoading: true, error: null }))

    try {
      const year = currentMonth.getFullYear()
      const month = currentMonth.getMonth()
      const data = await fetchCalendarData(selectedPropertyId, year, month)
      setState((prev) => ({
        properties: data.properties.length > 0 ? data.properties : prev.properties,
        roomTypes: data.roomTypes,
        availability: data.availability,
        isLoading: false,
        error: null,
      }))
    } catch (err) {
      let message = 'Failed to load calendar data.'
      if (isAxiosError(err) && err.response?.data?.detail) {
        message = err.response.data.detail
      }
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: message,
      }))
    }
  }, [currentMonth, selectedPropertyId])

  useEffect(() => {
    loadCalendar()
  }, [loadCalendar])

  const goToPrevMonth = useCallback(() => {
    setCurrentMonth((prev) => new Date(prev.getFullYear(), prev.getMonth() - 1, 1))
  }, [])

  const goToNextMonth = useCallback(() => {
    setCurrentMonth((prev) => new Date(prev.getFullYear(), prev.getMonth() + 1, 1))
  }, [])

  const goToToday = useCallback(() => {
    setCurrentMonth(new Date())
  }, [])

  const availabilityMap = useMemo(() => {
    const map = new Map<string, CalendarAvailability>()
    for (const a of state.availability) {
      map.set(`${a.room_type_id}:${a.date}`, a)
    }
    return map
  }, [state.availability])

  const handleBlockDates = useCallback(async (input: BlockDatesInput) => {
    await blockDates(input)
  }, [])

  return {
    currentMonth,
    selectedPropertyId,
    properties: state.properties,
    roomTypes: state.roomTypes,
    availability: state.availability,
    availabilityMap,
    isLoading: state.isLoading,
    error: state.error,
    goToPrevMonth,
    goToNextMonth,
    goToToday,
    setSelectedPropertyId,
    refresh: loadCalendar,
    blockDates: handleBlockDates,
  }
}
