import { useState, useEffect, useCallback, useRef } from 'react'
import {
  fetchProperties,
  fetchAvailability,
  fetchDashboardSummary,
  fetchWeekSummary,
  fetchOpenTasks,
  type Property,
  type DashboardSummary,
  type WeekSummaryData,
  type OpenTasksData,
} from '@/services/dashboardApi'

interface DashboardState {
  properties: Property[]
  summary: DashboardSummary
  weekSummary: WeekSummaryData
  openTasks: OpenTasksData
  isLoading: boolean
  error: string | null
}

const initialState: DashboardState = {
  properties: [],
  summary: { arrivals: 0, departures: 0, inHouse: 0, pendingCheckIns: 0 },
  weekSummary: { occupancyPercent: 0, adrByProperty: [] },
  openTasks: { otaQueueReview: 0, paymentFailures: 0, pendingRefunds: 0 },
  isLoading: true,
  error: null,
}

export function useDashboard() {
  const [state, setState] = useState<DashboardState>(initialState)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadDashboard = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: prev.properties.length === 0, error: null }))

    try {
      const today = new Date().toISOString().split('T')[0]
      const weekFromNow = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]

      const [properties, summary, weekSummary, openTasks] = await Promise.all([
        fetchProperties(),
        fetchDashboardSummary(),
        fetchWeekSummary(),
        fetchOpenTasks(),
      ])

      // Try to compute occupancy from availability API if we have properties
      let occupancyPercent = weekSummary.occupancyPercent
      if (properties.length > 0) {
        try {
          const availabilityData = await fetchAvailability({
            property_id: properties[0].id,
            check_in: today,
            check_out: weekFromNow,
          })
          const totalRooms = availabilityData.reduce((sum, d) => sum + d.total_count, 0)
          const availableRooms = availabilityData.reduce((sum, d) => sum + d.available_count, 0)
          if (totalRooms > 0) {
            occupancyPercent = Math.round(((totalRooms - availableRooms) / totalRooms) * 100)
          }
        } catch {
          // availability API not available — leave as-is (empty data, not zero stub)
        }
      }

      setState({
        properties,
        summary,
        weekSummary: { ...weekSummary, occupancyPercent },
        openTasks,
        isLoading: false,
        error: null,
      })
    } catch (err) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: err instanceof Error ? err.message : 'Failed to load dashboard data',
      }))
    }
  }, [])

  useEffect(() => {
    loadDashboard()

    intervalRef.current = setInterval(() => {
      loadDashboard()
    }, 60000)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [loadDashboard])

  return {
    ...state,
    refresh: loadDashboard,
  }
}
