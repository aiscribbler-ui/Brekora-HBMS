import { api, isAxiosError } from '@/lib/api'
import type { AxiosError } from 'axios'

export interface LoginCredentials {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  requires_2fa?: boolean
}

export interface RefreshResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export async function login(credentials: LoginCredentials): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>('/auth/login', credentials)
  return data
}

export async function refreshToken(refreshToken: string): Promise<RefreshResponse> {
  const { data } = await api.post<RefreshResponse>('/auth/refresh', {
    refresh_token: refreshToken,
  })
  return data
}

export async function logout(): Promise<void> {
  await api.post('/auth/logout')
}

export { isAxiosError, AxiosError }
