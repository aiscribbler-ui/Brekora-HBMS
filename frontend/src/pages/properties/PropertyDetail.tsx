import { useEffect, useState, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Dialog, DialogPanel, DialogTitle, Transition, TransitionChild } from '@headlessui/react'
import {
  ArrowLeftIcon,
  ArchiveBoxIcon,
  ArrowPathIcon,
  PlusIcon,
  XMarkIcon,
  TrashIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline'
import {
  getProperty,
  createProperty,
  updateProperty,
  uploadPropertyPhotos,
  type Property,
  type PropertyCreateInput,
} from '@/services/propertyApi'
import { isAxiosError } from '@/lib/api'
import PhotoUploader, { type PhotoFile } from '@/components/properties/PhotoUploader'

const propertySchema = z.object({
  name: z.string().min(1, 'Name is required').max(200, 'Name is too long'),
  address: z.string().min(1, 'Address is required'),
  city: z.string().optional(),
  state: z.string().optional(),
  country: z.string().optional(),
  postal_code: z.string().optional(),
  latitude: z.string().optional(),
  longitude: z.string().optional(),
  gstin: z.string().optional(),
  pan: z.string().optional(),
  owner_contact: z.string().optional(),
  default_check_in_time: z.string().optional(),
  default_check_out_time: z.string().optional(),
})

type PropertyFormData = z.infer<typeof propertySchema>

export default function PropertyDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isNew = id === 'new'

  const [property, setProperty] = useState<Property | null>(null)
  const [loading, setLoading] = useState(!isNew)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [amenities, setAmenities] = useState<string[]>([])
  const [amenityInput, setAmenityInput] = useState('')
  const [pendingPhotos, setPendingPhotos] = useState<PhotoFile[]>([])
  const [uploadingPhotos, setUploadingPhotos] = useState(false)
  const [confirmArchive, setConfirmArchive] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<PropertyFormData>({
    resolver: zodResolver(propertySchema),
    defaultValues: {
      name: '',
      address: '',
      city: '',
      state: '',
      country: '',
      postal_code: '',
      latitude: '',
      longitude: '',
      gstin: '',
      pan: '',
      owner_contact: '',
      default_check_in_time: '',
      default_check_out_time: '',
    },
  })

  useEffect(() => {
    if (isNew) {
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    getProperty(id!)
      .then((data) => {
        if (cancelled) return
        setProperty(data)
        setAmenities(data.amenities ?? [])
        reset({
          name: data.name,
          address: data.address,
          city: data.city ?? '',
          state: data.state ?? '',
          country: data.country ?? '',
          postal_code: data.postal_code ?? '',
          latitude: data.latitude ?? '',
          longitude: data.longitude ?? '',
          gstin: data.gstin ?? '',
          pan: data.pan ?? '',
          owner_contact: data.owner_contact ?? '',
          default_check_in_time: data.default_check_in_time ?? '',
          default_check_out_time: data.default_check_out_time ?? '',
        })
      })
      .catch((err) => {
        if (!cancelled) {
          if (isAxiosError(err) && err.response?.data?.detail) {
            setError(err.response.data.detail)
          } else {
            setError('Failed to load property.')
          }
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [id, isNew, reset])

  const onSubmit = async (form: PropertyFormData) => {
    setError(null)
    setSaving(true)
    try {
      const payload: PropertyCreateInput = {
        ...form,
        amenities,
        city: form.city || undefined,
        state: form.state || undefined,
        country: form.country || undefined,
        postal_code: form.postal_code || undefined,
        latitude: form.latitude || undefined,
        longitude: form.longitude || undefined,
        default_check_in_time: form.default_check_in_time || undefined,
        default_check_out_time: form.default_check_out_time || undefined,
      }
      if (isNew) {
        const created = await createProperty(payload)
        navigate(`/properties/${created.id}`, { replace: true })
      } else {
        const updated = await updateProperty(id!, payload)
        setProperty(updated)
        reset({
          name: updated.name,
          address: updated.address,
          city: updated.city ?? '',
          state: updated.state ?? '',
          country: updated.country ?? '',
          postal_code: updated.postal_code ?? '',
          latitude: updated.latitude ?? '',
          longitude: updated.longitude ?? '',
          gstin: updated.gstin ?? '',
          pan: updated.pan ?? '',
          owner_contact: updated.owner_contact ?? '',
          default_check_in_time: updated.default_check_in_time ?? '',
          default_check_out_time: updated.default_check_out_time ?? '',
        })
        setAmenities(updated.amenities ?? [])
      }
    } catch (err) {
      if (isAxiosError(err) && err.response?.data?.detail) {
        setError(err.response.data.detail)
      } else {
        setError('Failed to save property.')
      }
    } finally {
      setSaving(false)
    }
  }

  const handleUploadPhotos = useCallback(async () => {
    if (!id || isNew || pendingPhotos.length === 0) return
    setUploadingPhotos(true)
    setError(null)
    try {
      const files = pendingPhotos.map((p) => p.file)
      const updated = await uploadPropertyPhotos(id, files)
      setProperty(updated)
      setPendingPhotos([])
    } catch (err) {
      if (isAxiosError(err) && err.response?.data?.detail) {
        setError(err.response.data.detail)
      } else {
        setError('Failed to upload photos.')
      }
    } finally {
      setUploadingPhotos(false)
    }
  }, [id, isNew, pendingPhotos])

  const addAmenity = useCallback(() => {
    const value = amenityInput.trim()
    if (!value) return
    if (amenities.includes(value)) {
      setAmenityInput('')
      return
    }
    setAmenities((prev) => [...prev, value])
    setAmenityInput('')
  }, [amenityInput, amenities])

  const removeAmenity = useCallback((index: number) => {
    setAmenities((prev) => {
      const next = [...prev]
      next.splice(index, 1)
      return next
    })
  }, [])

  const toggleArchive = async () => {
    if (!property) return
    setError(null)
    try {
      const updated = await updateProperty(property.id, {
        is_archived: !property.is_archived,
      })
      setProperty(updated)
      setConfirmArchive(false)
    } catch (err) {
      if (isAxiosError(err) && err.response?.data?.detail) {
        setError(err.response.data.detail)
      } else {
        setError('Failed to update archive status.')
      }
    }
  }

  const handleDelete = async () => {
    if (!property) return
    setError(null)
    try {
      const { deleteProperty } = await import('@/services/propertyApi')
      await deleteProperty(property.id)
      navigate('/properties')
    } catch (err) {
      if (isAxiosError(err) && err.response?.data?.detail) {
        setError(err.response.data.detail)
      } else {
        setError('Failed to delete property.')
      }
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
        onClick={() => navigate('/properties')}
        className="inline-flex items-center gap-1 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 mb-4 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 rounded"
        aria-label="Back to properties"
      >
        <ArrowLeftIcon className="h-4 w-4" />
        Back to Properties
      </button>

      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          {isNew ? 'New Property' : property?.name}
        </h1>
        {!isNew && property && (
          <div className="flex items-center gap-2">
            {property.is_archived ? (
              <button
                onClick={() => setConfirmArchive(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md bg-success-light text-success hover:bg-success-light border border-success transition-colors focus:outline-none focus:ring-2 focus:ring-success focus:ring-offset-2"
                aria-label="Unarchive property"
              >
                <ArrowPathIcon className="h-4 w-4" aria-hidden="true" />
                Unarchive
              </button>
            ) : (
              <button
                onClick={() => setConfirmArchive(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md bg-gray-50 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600 border border-gray-200 dark:border-gray-600 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
                aria-label="Archive property"
              >
                <ArchiveBoxIcon className="h-4 w-4" aria-hidden="true" />
                Archive
              </button>
            )}
            <button
              onClick={() => setConfirmDelete(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30 border border-red-200 dark:border-red-800 transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
              aria-label="Delete property"
            >
              <TrashIcon className="h-4 w-4" aria-hidden="true" />
              Delete
            </button>
          </div>
        )}
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded border border-red-200 dark:border-red-800 text-sm" role="alert">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Basic Information</h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label htmlFor="name" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Property Name</label>
              <input
                id="name"
                type="text"
                aria-invalid={errors.name ? 'true' : 'false'}
                aria-describedby={errors.name ? 'name-error' : undefined}
                {...register('name')}
                className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500 dark:bg-gray-800 dark:text-gray-100"
              />
              {errors.name && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400" id="name-error" role="alert">{errors.name.message}</p>
              )}
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="address" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Address</label>
              <textarea
                id="address"
                rows={3}
                aria-invalid={errors.address ? 'true' : 'false'}
                aria-describedby={errors.address ? 'address-error' : undefined}
                {...register('address')}
                className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500 dark:bg-gray-800 dark:text-gray-100"
              />
              {errors.address && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400" id="address-error" role="alert">{errors.address.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="city" className="block text-sm font-medium text-gray-700 dark:text-gray-300">City</label>
              <input
                id="city"
                type="text"
                {...register('city')}
                className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:bg-gray-800 dark:text-gray-100"
              />
            </div>

            <div>
              <label htmlFor="state" className="block text-sm font-medium text-gray-700 dark:text-gray-300">State</label>
              <input
                id="state"
                type="text"
                {...register('state')}
                className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:bg-gray-800 dark:text-gray-100"
              />
            </div>

            <div>
              <label htmlFor="country" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Country</label>
              <input
                id="country"
                type="text"
                {...register('country')}
                className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:bg-gray-800 dark:text-gray-100"
              />
            </div>

            <div>
              <label htmlFor="postal_code" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Postal Code</label>
              <input
                id="postal_code"
                type="text"
                {...register('postal_code')}
                className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:bg-gray-800 dark:text-gray-100"
              />
            </div>

            <div>
              <label htmlFor="latitude" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Latitude</label>
              <input
                id="latitude"
                type="text"
                {...register('latitude')}
                className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:bg-gray-800 dark:text-gray-100"
              />
            </div>

            <div>
              <label htmlFor="longitude" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Longitude</label>
              <input
                id="longitude"
                type="text"
                {...register('longitude')}
                className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:bg-gray-800 dark:text-gray-100"
              />
            </div>

            <div>
              <label htmlFor="gstin" className="block text-sm font-medium text-gray-700 dark:text-gray-300">GSTIN</label>
              <input
                id="gstin"
                type="text"
                {...register('gstin')}
                className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:bg-gray-800 dark:text-gray-100"
              />
            </div>

            <div>
              <label htmlFor="pan" className="block text-sm font-medium text-gray-700 dark:text-gray-300">PAN</label>
              <input
                id="pan"
                type="text"
                {...register('pan')}
                className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:bg-gray-800 dark:text-gray-100"
              />
            </div>

            <div>
              <label htmlFor="owner_contact" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Owner Contact</label>
              <input
                id="owner_contact"
                type="text"
                {...register('owner_contact')}
                className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:bg-gray-800 dark:text-gray-100"
              />
            </div>

            <div className="grid grid-cols-2 gap-4 sm:col-span-2">
              <div>
                <label htmlFor="default_check_in_time" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Default Check-in Time
                </label>
                <input
                  id="default_check_in_time"
                  type="time"
                  {...register('default_check_in_time')}
                  className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:bg-gray-800 dark:text-gray-100"
                />
              </div>
              <div>
                <label htmlFor="default_check_out_time" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Default Check-out Time
                </label>
                <input
                  id="default_check_out_time"
                  type="time"
                  {...register('default_check_out_time')}
                  className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:bg-gray-800 dark:text-gray-100"
                />
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Amenities</h2>
          <div className="flex flex-wrap items-center gap-2">
            {amenities.map((a, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-brand-50 dark:bg-brand-900/20 text-brand-700 dark:text-brand-300 border border-brand-100 dark:border-brand-800"
              >
                {a}
                <button
                  type="button"
                  onClick={() => removeAmenity(i)}
                  className="hover:text-brand-900 dark:hover:text-brand-100"
                  aria-label={`Remove ${a}`}
                >
                  <XMarkIcon className="h-3 w-3" />
                </button>
              </span>
            ))}
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={amenityInput}
                onChange={(e) => setAmenityInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    addAmenity()
                  }
                }}
                placeholder="Add amenity..."
                className="rounded-md border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:bg-gray-800 dark:text-gray-100"
              />
              <button
                type="button"
                onClick={addAmenity}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 text-sm font-medium rounded-md bg-brand-600 text-white hover:bg-brand-700 transition-colors"
              >
                <PlusIcon className="h-3 w-3" />
                Add
              </button>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Photos</h2>
          {property?.photos && property.photos.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
              {property.photos.map((photo, idx) => (
                <div key={idx} className="rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700">
                  <img
                    src={photo.url}
                    alt={photo.caption || `Property photo ${idx + 1}`}
                    className="h-24 w-full object-cover"
                  />
                </div>
              ))}
            </div>
          )}
          <PhotoUploader
            photos={pendingPhotos}
            onChange={setPendingPhotos}
            onUpload={isNew ? undefined : handleUploadPhotos}
            disabled={uploadingPhotos}
          />
        </div>

        <div className="flex items-center gap-3 pt-2">
          <button
            type="submit"
            disabled={saving || (!isDirty && !isNew)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-md hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
          <button
            type="button"
            onClick={() => navigate('/properties')}
            className="inline-flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
          >
            Cancel
          </button>
          {!isNew && (
            <button
              type="button"
              onClick={() => navigate(`/properties/${id}/room-types`)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 text-brand-700 dark:text-brand-300 border border-brand-300 dark:border-brand-700 text-sm font-medium rounded-md hover:bg-brand-50 dark:hover:bg-brand-900/20 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
            >
              Manage Room Types
            </button>
          )}
        </div>
      </form>

      {/* Archive confirmation modal */}
      <Transition show={confirmArchive} as="div">
        <Dialog onClose={() => setConfirmArchive(false)} className="relative z-50">
          <TransitionChild
            enter="ease-out duration-200"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="ease-in duration-150"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
          </TransitionChild>
          <div className="fixed inset-0 flex items-center justify-center p-4">
            <TransitionChild
              enter="ease-out duration-200"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-150"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <DialogPanel className="w-full max-w-md bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6">
                <div className="flex items-center gap-3 mb-4">
                  <ExclamationTriangleIcon className="h-6 w-6 text-amber-500" />
                  <DialogTitle className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                    {property?.is_archived ? 'Unarchive Property' : 'Archive Property'}
                  </DialogTitle>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
                  Are you sure you want to {property?.is_archived ? 'unarchive' : 'archive'} this property?
                </p>
                <div className="flex items-center justify-end gap-3">
                  <button
                    onClick={() => setConfirmArchive(false)}
                    className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={toggleArchive}
                    className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 transition-colors"
                  >
                    Confirm
                  </button>
                </div>
              </DialogPanel>
            </TransitionChild>
          </div>
        </Dialog>
      </Transition>

      {/* Delete confirmation modal */}
      <Transition show={confirmDelete} as="div">
        <Dialog onClose={() => setConfirmDelete(false)} className="relative z-50">
          <TransitionChild
            enter="ease-out duration-200"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="ease-in duration-150"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
          </TransitionChild>
          <div className="fixed inset-0 flex items-center justify-center p-4">
            <TransitionChild
              enter="ease-out duration-200"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-150"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <DialogPanel className="w-full max-w-md bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6">
                <div className="flex items-center gap-3 mb-4">
                  <ExclamationTriangleIcon className="h-6 w-6 text-red-500" />
                  <DialogTitle className="text-lg font-semibold text-gray-900 dark:text-gray-100">Delete Property</DialogTitle>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
                  This action cannot be undone. All room types and associated data will be permanently removed.
                </p>
                <div className="flex items-center justify-end gap-3">
                  <button
                    onClick={() => setConfirmDelete(false)}
                    className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleDelete}
                    className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 transition-colors"
                  >
                    Delete
                  </button>
                </div>
              </DialogPanel>
            </TransitionChild>
          </div>
        </Dialog>
      </Transition>
    </div>
  )
}
