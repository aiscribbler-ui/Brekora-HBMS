import { api } from '@/lib/api'

export interface FeatureFlag {
  id: string
  key: string
  value: boolean
  description: string
}

export interface SystemConfig {
  gstRate: number
  partnerAttributionLookbackDays: number
}

export type UserRole = 'Admin' | 'Owner' | 'Manager' | 'Partner' | 'Guest'

export interface User {
  id: string
  name: string
  email: string
  role: UserRole
  status: 'active' | 'inactive'
}

export interface OtaSettings {
  autoConfirmAirbnb: boolean
  autoConfirmMmt: boolean
  autoConfirmGoibibo: boolean
  confidenceThreshold: number
}

export async function fetchFeatureFlags(): Promise<FeatureFlag[]> {
  const { data } = await api.get<FeatureFlag[]>('/feature-flags/')
  return data
}

export async function updateFeatureFlag(id: string, value: boolean): Promise<FeatureFlag> {
  const { data } = await api.patch<FeatureFlag>(`/feature-flags/${id}`, { value })
  return data
}

export async function fetchSystemConfig(): Promise<SystemConfig> {
  const { data } = await api.get<SystemConfig>('/gst/rate')
  return data
}

export async function updateSystemConfig(config: Partial<SystemConfig>): Promise<SystemConfig> {
  const { data } = await api.patch<SystemConfig>('/gst/rate', config)
  return data
}

export async function fetchUsers(): Promise<User[]> {
  const { data } = await api.get<User[]>('/users/')
  return data
}

export async function updateUser(id: string, payload: Partial<User>): Promise<User> {
  const { data } = await api.patch<User>(`/users/${id}`, payload)
  return data
}

export async function forceLogoutUser(id: string): Promise<void> {
  await api.delete(`/admin/users/${id}/sessions`)
}

export async function fetchOtaSettings(): Promise<OtaSettings> {
  try {
    const { data } = await api.get<OtaSettings>('/system-config/ota')
    return data
  } catch {
    return {
      autoConfirmAirbnb: false,
      autoConfirmMmt: false,
      autoConfirmGoibibo: false,
      confidenceThreshold: 0.9,
    }
  }
}

export async function updateOtaSettings(settings: OtaSettings): Promise<OtaSettings> {
  try {
    const { data } = await api.patch<OtaSettings>('/system-config/ota', settings)
    return data
  } catch {
    return settings
  }
}
