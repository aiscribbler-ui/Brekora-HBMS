import { api } from '@/lib/api'

export interface PropertyPhoto {
  url: string
  caption?: string
}

export interface Property {
  id: string
  name: string
  address: string
  gstin?: string
  pan?: string
  owner_contact?: string
  photos: PropertyPhoto[]
  amenities: string[]
  default_check_in_time?: string
  default_check_out_time?: string
  is_active: boolean
  is_archived: boolean
}

export interface PropertyCreateInput {
  name: string
  address: string
  gstin?: string
  pan?: string
  owner_contact?: string
  amenities?: string[]
  default_check_in_time?: string
  default_check_out_time?: string
}

export interface PropertyUpdateInput {
  name?: string
  address?: string
  gstin?: string
  pan?: string
  owner_contact?: string
  amenities?: string[]
  default_check_in_time?: string
  default_check_out_time?: string
  is_active?: boolean
  is_archived?: boolean
}

export interface RoomTypePhoto {
  url: string
  caption?: string
}

export interface RoomType {
  id: string
  property_id: string
  name: string
  description?: string
  count: number
  base_capacity: number
  max_capacity: number
  default_rate: string
  min_stay?: number
  max_stay?: number
  photos: RoomTypePhoto[]
  is_active: boolean
  is_archived: boolean
}

export interface RoomTypeCreateInput {
  name: string
  description?: string
  count: number
  base_capacity: number
  max_capacity: number
  default_rate: string
  min_stay?: number
  max_stay?: number
}

export interface RoomTypeUpdateInput {
  name?: string
  description?: string
  count?: number
  base_capacity?: number
  max_capacity?: number
  default_rate?: string
  min_stay?: number
  max_stay?: number
  is_active?: boolean
  is_archived?: boolean
}

export async function getProperties(): Promise<Property[]> {
  const { data } = await api.get<Property[]>('/properties')
  return data
}

export async function getProperty(id: string): Promise<Property> {
  const { data } = await api.get<Property>(`/properties/${id}`)
  return data
}

export async function createProperty(input: PropertyCreateInput): Promise<Property> {
  const { data } = await api.post<Property>('/properties', input)
  return data
}

export async function updateProperty(id: string, input: PropertyUpdateInput): Promise<Property> {
  const { data } = await api.patch<Property>(`/properties/${id}`, input)
  return data
}

export async function deleteProperty(id: string): Promise<void> {
  await api.delete(`/properties/${id}`)
}

export async function uploadPropertyPhotos(id: string, files: File[]): Promise<Property> {
  const formData = new FormData()
  files.forEach((file) => formData.append('photos', file))
  const { data } = await api.post<Property>(`/properties/${id}/photos`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return data
}

export async function getRoomTypes(propertyId: string): Promise<RoomType[]> {
  const { data } = await api.get<RoomType[]>(`/properties/${propertyId}/room-types`)
  return data
}

export async function getRoomType(propertyId: string, roomTypeId: string): Promise<RoomType> {
  const { data } = await api.get<RoomType>(`/properties/${propertyId}/room-types/${roomTypeId}`)
  return data
}

export async function createRoomType(propertyId: string, input: RoomTypeCreateInput): Promise<RoomType> {
  const { data } = await api.post<RoomType>(`/properties/${propertyId}/room-types`, input)
  return data
}

export async function updateRoomType(
  propertyId: string,
  roomTypeId: string,
  input: RoomTypeUpdateInput,
): Promise<RoomType> {
  const { data } = await api.patch<RoomType>(`/properties/${propertyId}/room-types/${roomTypeId}`, input)
  return data
}

export async function deleteRoomType(propertyId: string, roomTypeId: string): Promise<void> {
  await api.delete(`/properties/${propertyId}/room-types/${roomTypeId}`)
}
