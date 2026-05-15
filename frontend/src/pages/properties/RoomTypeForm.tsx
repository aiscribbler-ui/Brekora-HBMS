import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useForm, type SubmitHandler } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  ArrowLeftIcon,
} from '@heroicons/react/24/outline'
import {
  getRoomType,
  createRoomType,
  updateRoomType,
  type RoomType,
  type RoomTypeCreateInput,
} from '@/services/propertyApi'
import { isAxiosError } from '@/lib/api'
import PhotoUploader, { type PhotoFile } from '@/components/properties/PhotoUploader'

const roomTypeSchema = z.object({
  name: z.string().min(1, 'Name is required').max(200, 'Name is too long'),
  description: z.string().optional(),
  count: z.coerce.number().int().min(1, 'Count must be at least 1'),
  base_capacity: z.coerce.number().int().min(1, 'Base capacity must be at least 1'),
  max_capacity: z.coerce.number().int().min(1, 'Max capacity must be at least 1'),
  default_rate: z.string().min(1, 'Default rate is required'),
  min_stay: z.preprocess(
    (val) => (val === '' || val === undefined ? undefined : val),
    z.coerce.number().int().min(1, 'Min stay must be at least 1').optional(),
  ),
  max_stay: z.preprocess(
    (val) => (val === '' || val === undefined ? undefined : val),
    z.coerce.number().int().optional(),
  ),
}).refine((data) => data.max_capacity >= data.base_capacity, {
  message: 'Max capacity must be greater than or equal to base capacity',
  path: ['max_capacity'],
})

type RoomTypeFormData = z.infer<typeof roomTypeSchema>

export default function RoomTypeForm() {
  const { id: propertyId, roomTypeId } = useParams<{ id: string; roomTypeId: string }>()
  const navigate = useNavigate()
  const isNew = roomTypeId === 'new'

  const [roomType, setRoomType] = useState<RoomType | null>(null)
  const [loading, setLoading] = useState(!isNew)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pendingPhotos, setPendingPhotos] = useState<PhotoFile[]>([])

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isDirty },
  } = useForm<RoomTypeFormData>({
    resolver: zodResolver(roomTypeSchema),
    defaultValues: {
      name: '',
      description: '',
      count: 1,
      base_capacity: 2,
      max_capacity: 3,
      default_rate: '',
      min_stay: undefined,
      max_stay: undefined,
    },
  })

  const countValue = watch('count') || 0

  useEffect(() => {
    if (isNew || !propertyId || !roomTypeId) {
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    getRoomType(propertyId, roomTypeId)
      .then((data) => {
        if (cancelled) return
        setRoomType(data)
        reset({
          name: data.name,
          description: data.description ?? '',
          count: data.count,
          base_capacity: data.base_capacity,
          max_capacity: data.max_capacity,
          default_rate: data.default_rate,
          min_stay: data.min_stay ?? undefined,
          max_stay: data.max_stay ?? undefined,
        })
      })
      .catch((err) => {
        if (!cancelled) {
          if (isAxiosError(err) && err.response?.data?.detail) {
            setError(err.response.data.detail)
          } else {
            setError('Failed to load room type.')
          }
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [propertyId, roomTypeId, isNew, reset])

  const onSubmit: SubmitHandler<RoomTypeFormData> = async (form) => {
    if (!propertyId) return
    setError(null)
    setSaving(true)
    try {
      const payload: RoomTypeCreateInput = {
        name: form.name,
        description: form.description || undefined,
        count: form.count,
        base_capacity: form.base_capacity,
        max_capacity: form.max_capacity,
        default_rate: form.default_rate,
        min_stay: form.min_stay ? Number(form.min_stay) : undefined,
        max_stay: form.max_stay ? Number(form.max_stay) : undefined,
      }
      if (isNew) {
        await createRoomType(propertyId, payload)
        navigate(`/properties/${propertyId}/room-types`)
      } else {
        const updated = await updateRoomType(propertyId, roomTypeId!, payload)
        setRoomType(updated)
        reset({
          name: updated.name,
          description: updated.description ?? '',
          count: updated.count,
          base_capacity: updated.base_capacity,
          max_capacity: updated.max_capacity,
          default_rate: updated.default_rate,
          min_stay: updated.min_stay ?? undefined,
          max_stay: updated.max_stay ?? undefined,
        })
      }
    } catch (err) {
      if (isAxiosError(err) && err.response?.data?.detail) {
        setError(err.response.data.detail)
      } else {
        setError('Failed to save room type.')
      }
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto space-y-4">
        <div className="h-8 bg-gray-100 dark:bg-gray-700 rounded w-1/3 animate-pulse" />
        <div className="h-64 bg-gray-100 dark:bg-gray-700 rounded-lg animate-pulse" />
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto">
      <button
        onClick={() => navigate(`/properties/${propertyId}/room-types`)}
        className="inline-flex items-center gap-1 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 mb-4"
      >
        <ArrowLeftIcon className="h-4 w-4" />
        Back to Room Types
      </button>

      <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">
        {isNew ? 'New Room Type' : roomType?.name}
      </h1>

      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded border border-red-200 dark:border-red-800 text-sm" role="alert">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Room Type Details</h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label htmlFor="name" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Name</label>
              <input
                id="name"
                type="text"
                {...register('name')}
                className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:bg-gray-800 dark:text-gray-100"
              />
              {errors.name && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.name.message}</p>
              )}
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="description" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Description</label>
              <textarea
                id="description"
                rows={3}
                {...register('description')}
                className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:bg-gray-800 dark:text-gray-100"
              />
            </div>

            <div>
              <label htmlFor="count" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Room Count</label>
              <input
                id="count"
                type="number"
                min={1}
                {...register('count')}
                className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:bg-gray-800 dark:text-gray-100"
              />
              {errors.count && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.count.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="default_rate" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Default Rate</label>
              <input
                id="default_rate"
                type="text"
                placeholder="0.00"
                {...register('default_rate')}
                className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:bg-gray-800 dark:text-gray-100"
              />
              {errors.default_rate && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.default_rate.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="base_capacity" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Base Capacity</label>
              <input
                id="base_capacity"
                type="number"
                min={1}
                {...register('base_capacity')}
                className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:bg-gray-800 dark:text-gray-100"
              />
              {errors.base_capacity && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.base_capacity.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="max_capacity" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Max Capacity</label>
              <input
                id="max_capacity"
                type="number"
                min={1}
                {...register('max_capacity')}
                className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:bg-gray-800 dark:text-gray-100"
              />
              {errors.max_capacity && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.max_capacity.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="min_stay" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Min Stay (nights)</label>
              <input
                id="min_stay"
                type="number"
                min={1}
                {...register('min_stay')}
                className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:bg-gray-800 dark:text-gray-100"
              />
              {errors.min_stay && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.min_stay.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="max_stay" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Max Stay (nights)</label>
              <input
                id="max_stay"
                type="number"
                min={1}
                {...register('max_stay')}
                className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:bg-gray-800 dark:text-gray-100"
              />
              {errors.max_stay && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.max_stay.message}</p>
              )}
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Inventory Buffer</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">Set how many rooms to hold back from public availability.</p>
          <div className="flex items-center gap-4">
            <input
              type="range"
              min={0}
              max={countValue}
              defaultValue={0}
              className="flex-1 accent-brand-600"
              aria-label="Inventory buffer"
            />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300 w-12 text-right">0</span>
          </div>
          <p className="text-xs text-gray-400 dark:text-gray-500">Placeholder: buffer slider (0 to {countValue})</p>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Photos</h2>
          {roomType?.photos && roomType.photos.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
              {roomType.photos.map((photo, idx) => (
                <div key={idx} className="rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700">
                  <img
                    src={photo.url}
                    alt={photo.caption || `Room type photo ${idx + 1}`}
                    className="h-24 w-full object-cover"
                  />
                </div>
              ))}
            </div>
          )}
          <PhotoUploader photos={pendingPhotos} onChange={setPendingPhotos} />
        </div>

        <div className="flex items-center gap-3 pt-2">
          <button
            type="submit"
            disabled={saving || (!isDirty && !isNew)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-md hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
          <button
            type="button"
            onClick={() => navigate(`/properties/${propertyId}/room-types`)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
