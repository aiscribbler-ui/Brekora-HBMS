import { api } from '@/lib/api'

export interface PnLSummary {
  gross_revenue: number
  ota_commission: number
  partner_commission: number
  gst: number
  net_distributable: number
}

export interface PayoutRecord {
  owner_percentage: number
  brekora_percentage: number
  net_distributable: number
  owner_share: number
  brekora_share: number
  month: string
  status?: string
  paid_at?: string | null
}

export interface StatementBooking {
  booking_id: string
  source: 'Direct' | 'OTA'
  gross_amount: number
  ota_commission: number
  partner_commission: number
  gst: number
  net_amount: number
}

export interface Statement {
  property_id: string
  month: string
  bookings: StatementBooking[]
}

export async function getPnl(propertyId: string, month: string): Promise<PnLSummary> {
  const { data } = await api.get<PnLSummary>('/owner/pnl', { params: { property_id: propertyId, month } })
  return data
}

export async function getPayout(propertyId: string, month: string): Promise<PayoutRecord> {
  const { data } = await api.get<PayoutRecord>('/owner/payout', { params: { property_id: propertyId, month } })
  return data
}

export async function getStatement(propertyId: string, month: string): Promise<Statement> {
  const { data } = await api.get<Statement>('/owner/statement', { params: { property_id: propertyId, month } })
  return data
}
