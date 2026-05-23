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

export interface GmailStatus {
  connected: boolean
  status: string
  message?: string
  email?: string
  messages_total?: number
  threads_total?: number
}

export async function fetchGmailStatus(): Promise<GmailStatus> {
  const { data } = await api.get<GmailStatus>('/ota/gmail/status')
  return data
}

export async function initiateGmailAuth(): Promise<{ auth_url: string; state: string }> {
  const { data } = await api.get<{ auth_url: string; state: string }>('/ota/gmail/auth')
  return data
}

export async function disconnectGmail(): Promise<void> {
  await api.post('/ota/gmail/disconnect')
}

export interface GmailConfig {
  client_id: string | null
  client_secret: string | null
  configured: boolean
  redirect_uri: string | null
}

export async function fetchGmailConfig(): Promise<GmailConfig> {
  const { data } = await api.get<GmailConfig>('/ota/gmail/config')
  return data
}

export async function updateGmailConfig(config: { client_id: string; client_secret: string; redirect_uri?: string }): Promise<GmailConfig> {
  const { data } = await api.patch<GmailConfig>('/ota/gmail/config', config)
  return data
}

export interface OtaSourceSetting {
  id: string
  ota_source: 'airbnb' | 'mmt' | 'goibibo'
  auto_confirm: boolean
  min_confidence: number
  is_active: boolean
}

const SOURCE_MAP: Record<string, keyof Omit<OtaSettings, 'confidenceThreshold'>> = {
  airbnb: 'autoConfirmAirbnb',
  mmt: 'autoConfirmMmt',
  goibibo: 'autoConfirmGoibibo',
}

export async function fetchOtaSettings(): Promise<OtaSettings> {
  try {
    const { data } = await api.get<OtaSourceSetting[]>('/ota/settings/')
    const result: OtaSettings = {
      autoConfirmAirbnb: false,
      autoConfirmMmt: false,
      autoConfirmGoibibo: false,
      confidenceThreshold: 0.9,
    }
    let minConfidence = 0.9
    for (const item of data) {
      const key = SOURCE_MAP[item.ota_source]
      if (key) {
        result[key] = item.auto_confirm
      }
      if (item.min_confidence > 0) {
        minConfidence = item.min_confidence
      }
    }
    result.confidenceThreshold = minConfidence
    return result
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
  const sources: { ota_source: string; auto_confirm: boolean }[] = [
    { ota_source: 'airbnb', auto_confirm: settings.autoConfirmAirbnb },
    { ota_source: 'mmt', auto_confirm: settings.autoConfirmMmt },
    { ota_source: 'goibibo', auto_confirm: settings.autoConfirmGoibibo },
  ]
  await Promise.all(
    sources.map((s) =>
      api.put('/ota/settings/', {
        ota_source: s.ota_source,
        auto_confirm: s.auto_confirm,
        min_confidence: settings.confidenceThreshold,
        is_active: true,
      })
    )
  )
  return settings
}
