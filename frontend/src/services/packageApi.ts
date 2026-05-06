import { api } from '@/lib/api'

export interface PackageComposition {
  id: string
  package_id: string
  org_id: string
  room_type_id: string
  quantity: number
  nights: number
  created_at: string
  updated_at: string
}

export interface PackageAddOn {
  id: string
  package_id: string
  org_id: string
  add_on_id: string
  quantity: number
  is_included: boolean
  created_at: string
  updated_at: string
}

export interface Package {
  id: string
  org_id: string
  property_id: string
  name: string
  description: string | null
  status: string
  base_price: string
  dynamic_pricing_rules: Record<string, unknown> | null
  date_constraints: Record<string, unknown> | null
  max_occupancy: number | null
  cancellation_policy_id: string | null
  is_active: boolean
  is_archived: boolean
  created_at: string
  updated_at: string
  compositions: PackageComposition[]
  add_ons: PackageAddOn[]
}

export interface PackageCreateInput {
  property_id: string
  name: string
  description?: string
  status?: string
  base_price?: string
  dynamic_pricing_rules?: Record<string, unknown>
  date_constraints?: Record<string, unknown>
  max_occupancy?: number
  cancellation_policy_id?: string
  is_active?: boolean
  is_featured?: boolean
}

export interface PackageUpdateInput {
  name?: string
  description?: string
  status?: string
  base_price?: string
  dynamic_pricing_rules?: Record<string, unknown>
  date_constraints?: Record<string, unknown>
  max_occupancy?: number
  cancellation_policy_id?: string
  is_active?: boolean
  is_archived?: boolean
  is_featured?: boolean
}

export interface CompositionCreateInput {
  room_type_id: string
  quantity: number
  nights: number
}

export interface AddOnCreateInput {
  add_on_id: string
  quantity: number
  is_included: boolean
}

export interface AddOn {
  id: string
  org_id: string
  property_id: string
  name: string
  description: string | null
  type: 'slot' | 'day' | 'package_instance'
  default_capacity: number
  unit_price: string
  is_active: boolean
  is_archived: boolean
  created_at: string
  updated_at: string
}

export async function getPackages(): Promise<Package[]> {
  const { data } = await api.get<Package[]>('/packages/')
  return data
}

export async function getPackage(id: string): Promise<Package> {
  const { data } = await api.get<Package>(`/packages/${id}`)
  return data
}

export async function createPackage(input: PackageCreateInput): Promise<Package> {
  const { data } = await api.post<Package>('/packages/', input)
  return data
}

export async function updatePackage(id: string, input: PackageUpdateInput): Promise<Package> {
  const { data } = await api.patch<Package>(`/packages/${id}`, input)
  return data
}

export async function deletePackage(id: string): Promise<void> {
  await api.delete(`/packages/${id}`)
}

export async function getCompositions(packageId: string): Promise<PackageComposition[]> {
  const { data } = await api.get<PackageComposition[]>(`/packages/${packageId}/compositions`)
  return data
}

export async function addComposition(
  packageId: string,
  input: CompositionCreateInput,
): Promise<PackageComposition> {
  const { data } = await api.post<PackageComposition>(`/packages/${packageId}/compositions`, input)
  return data
}

export async function removeComposition(compositionId: string): Promise<void> {
  await api.delete(`/packages/compositions/${compositionId}`)
}

export async function getPackageAddOns(packageId: string): Promise<PackageAddOn[]> {
  const { data } = await api.get<PackageAddOn[]>(`/packages/${packageId}/add-ons`)
  return data
}

export async function addPackageAddOn(
  packageId: string,
  input: AddOnCreateInput,
): Promise<PackageAddOn> {
  const { data } = await api.post<PackageAddOn>(`/packages/${packageId}/add-ons`, input)
  return data
}

export async function removePackageAddOn(packageAddOnId: string): Promise<void> {
  await api.delete(`/packages/add-ons/${packageAddOnId}`)
}

export async function getAddOns(): Promise<AddOn[]> {
  const { data } = await api.get<AddOn[]>('/add-ons/')
  return data
}
