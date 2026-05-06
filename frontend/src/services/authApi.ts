import { api, isAxiosError } from '@/lib/api'
import type { AxiosError } from 'axios'

export interface LoginCredentials {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string | null
  refresh_token: string | null
  token_type: string
  expires_in?: number | null
  temp_token?: string | null
  requires_2fa?: boolean
  session_id?: string | null
}

export interface RefreshResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in?: number
  session_id?: string | null
}

export interface TwoFactorLoginVerifyPayload {
  temp_token: string
  token: string
}

export async function login(credentials: LoginCredentials): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>('/auth/login', credentials)
  return data
}

export async function verifyTwoFactorLogin(
  payload: TwoFactorLoginVerifyPayload,
): Promise<RefreshResponse> {
  const { data } = await api.post<RefreshResponse>('/auth/2fa/login-verify', payload)
  return data
}

export async function refreshToken(refreshToken: string): Promise<RefreshResponse> {
  const { data } = await api.post<RefreshResponse>('/auth/refresh', {
    refresh_token: refreshToken,
  })
  return data
}

export async function logout(refreshToken: string, sessionId?: string | null): Promise<void> {
  const headers: Record<string, string> = {}
  if (sessionId) headers['X-Session-ID'] = sessionId
  await api.post(
    '/auth/logout',
    { refresh_token: refreshToken },
    { headers },
  )
}

export interface TwoFactorSetupResponse {
  secret: string
  provisioning_uri: string
}

export async function setupTwoFactor(): Promise<TwoFactorSetupResponse> {
  const { data } = await api.post<TwoFactorSetupResponse>('/auth/2fa/setup')
  return data
}

export async function verifyTwoFactorEnrol(secret: string, token: string): Promise<void> {
  await api.post('/auth/2fa/verify', { secret, token })
}

export async function disableTwoFactor(token: string): Promise<void> {
  await api.post('/auth/2fa/disable', { token })
}

export interface MeResponse {
  id: string
  email: string
  role: string
  name?: string | null
  is_2fa_enabled?: boolean
  is_active?: boolean
}

export async function getMe(): Promise<MeResponse> {
  const { data } = await api.get<MeResponse>('/auth/me')
  return data
}

export interface GoogleAuthRawResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  session_id: string
  user: {
    id: string
    email: string
    role?: string | null
    first_name?: string | null
    last_name?: string | null
  }
}

export async function googleLogin(idToken: string): Promise<GoogleAuthRawResponse> {
  const { data } = await api.post<GoogleAuthRawResponse>('/auth/google', { id_token: idToken })
  return data
}

export interface RegisterGuestInput {
  email: string
  password: string
  first_name?: string
  last_name?: string
  phone?: string
}

export interface RegisterGuestResponse {
  id: string
  email: string
}

export async function registerGuest(data: RegisterGuestInput): Promise<RegisterGuestResponse> {
  const { data: responseData } = await api.post<RegisterGuestResponse>('/auth/register', data)
  return responseData
}

export { isAxiosError, AxiosError }
