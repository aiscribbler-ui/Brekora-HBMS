import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  PlusIcon,
  ArrowLeftIcon,
  PencilIcon,
  ArchiveBoxIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  BuildingOfficeIcon,
} from '@heroicons/react/24/outline'
import { Dialog, DialogPanel, DialogTitle, Transition, TransitionChild } from '@headlessui/react'
import { getRoomTypes, updateRoomType, type RoomType, getProperty } from '@/services/propertyApi'
import { isAxiosError } from '@/lib/api'

export default function RoomTypeList() {
  const { id: propertyId } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [roomTypes, setRoomTypes] = useState<RoomType[]>([])
  const [propertyName, setPropertyName] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [confirmArchive, setConfirmArchive] = useState<RoomType | null>(null)

  useEffect(() => {
    if (!propertyId) return
    let cancelled = false
    setLoading(true)
    setError(null)

    Promise.all([
      getProperty(propertyId).then((p) => {
        if (!cancelled) setPropertyName(p.name)
      }),
      getRoomTypes(propertyId).then((data) => {
        if (!cancelled) setRoomTypes(data)
      }),
    ]).catch((err) => {
      if (!cancelled) {
        if (isAxiosError(err) && err.response?.data?.detail) {
          setError(err.response.data.detail)
        } else {
          setError('Failed to load room types.')
        }
      }
    }).finally(() => {
      if (!cancelled) setLoading(false)
    })

    return () => { cancelled = true }
  }, [propertyId])

  const activeCount = useMemo(() => roomTypes.filter((r) => r.is_active && !r.is_archived).length, [roomTypes])

  const toggleArchive = async (roomType: RoomType) => {
    if (!propertyId) return
    setError(null)
    try {
      const updated = await updateRoomType(propertyId, roomType.id, {
        is_archived: !roomType.is_archived,
      })
      setRoomTypes((prev) => prev.map((r) => (r.id === updated.id ? updated : r)))
      setConfirmArchive(null)
    } catch (err) {
      if (isAxiosError(err) && err.response?.data?.detail) {
        setError(err.response.data.detail)
      } else {
        setError('Failed to update room type.')
      }
    }
  }

  return (
    <div className="max-w-5xl mx-auto">
      <button
        onClick={() => navigate(`/properties/${propertyId}`)}
        className="inline-flex items-center gap-1 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 mb-4 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 rounded"
        aria-label="Back to property"
      >
        <ArrowLeftIcon className="h-4 w-4" aria-hidden="true" />
        Back to Property
      </button>

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Room Types</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {propertyName && `${propertyName} — `}{activeCount} active room type{activeCount !== 1 ? 's' : ''}
          </p>
        </div>
        <button
          onClick={() => navigate(`/properties/${propertyId}/room-types/new`)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-md hover:bg-brand-700 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
          aria-label="Add room type"
        >
          <PlusIcon className="h-4 w-4" />
          Add Room Type
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded border border-red-200 dark:border-red-800 text-sm" role="alert">
          {error}
        </div>
      )}

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-16 bg-gray-100 dark:bg-gray-700 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : roomTypes.length === 0 ? (
        <div className="text-center py-16 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <BuildingOfficeIcon className="mx-auto h-10 w-10 text-gray-300 dark:text-gray-600" />
          <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">No room types found.</p>
          <button
            onClick={() => navigate(`/properties/${propertyId}/room-types/new`)}
            className="mt-2 text-sm text-brand-600 hover:underline"
          >
            Create a room type
          </button>
        </div>
      ) : (
        <>
          {/* Desktop table */}
          <div className="hidden md:block bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Name</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Count</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Capacity</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Default Rate</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Status</th>
                  <th scope="col" className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {roomTypes.map((rt) => (
                  <tr key={rt.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-gray-100">{rt.name}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{rt.count}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
                      {rt.base_capacity} / {rt.max_capacity}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{rt.default_rate}</td>
                    <td className="px-4 py-3">
                      {rt.is_archived ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300">
                          Archived
                        </span>
                      ) : rt.is_active ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-success-light text-success-dark">
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-warning-light text-warning-dark">
                          Inactive
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="inline-flex items-center gap-2">
                        <button
                          onClick={() => navigate(`/properties/${propertyId}/room-types/${rt.id}`)}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-md bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-1"
                          aria-label={`Edit ${rt.name}`}
                        >
                          <PencilIcon className="h-3 w-3" aria-hidden="true" />
                          Edit
                        </button>
                        <button
                          onClick={() => setConfirmArchive(rt)}
                          className={[
                            'inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-md border transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1',
                            rt.is_archived
                              ? 'bg-success-light text-success border-success hover:bg-success-light focus:ring-success'
                              : 'bg-gray-50 dark:bg-gray-700 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-600 focus:ring-gray-500',
                          ].join(' ')}
                          aria-label={`${rt.is_archived ? 'Unarchive' : 'Archive'} ${rt.name}`}
                        >
                          {rt.is_archived ? <ArrowPathIcon className="h-3 w-3" aria-hidden="true" /> : <ArchiveBoxIcon className="h-3 w-3" aria-hidden="true" />}
                          {rt.is_archived ? 'Unarchive' : 'Archive'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile cards */}
          <div className="md:hidden space-y-3">
            {roomTypes.map((rt) => (
              <div
                key={rt.id}
                className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4"
              >
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">{rt.name}</h3>
                  {rt.is_archived ? (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300">
                      Archived
                    </span>
                  ) : rt.is_active ? (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-success-light text-success-dark">
                      Active
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-warning-light text-warning-dark">
                      Inactive
                    </span>
                  )}
                </div>
                <div className="mt-2 text-xs text-gray-600 dark:text-gray-400 space-y-1">
                  <p>Rooms: {rt.count} | Capacity: {rt.base_capacity} / {rt.max_capacity}</p>
                  <p>Rate: {rt.default_rate}</p>
                </div>
                <div className="mt-3 flex items-center gap-2">
                  <button
                    onClick={() => navigate(`/properties/${propertyId}/room-types/${rt.id}`)}
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-md bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-1"
                    aria-label={`Edit ${rt.name}`}
                  >
                    <PencilIcon className="h-3 w-3" aria-hidden="true" />
                    Edit
                  </button>
                  <button
                    onClick={() => setConfirmArchive(rt)}
                    className={[
                      'inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-md border transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1',
                      rt.is_archived
                        ? 'bg-success-light text-success border-success hover:bg-success-light focus:ring-success'
                        : 'bg-gray-50 dark:bg-gray-700 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-600 focus:ring-gray-500',
                    ].join(' ')}
                    aria-label={`${rt.is_archived ? 'Unarchive' : 'Archive'} ${rt.name}`}
                  >
                    {rt.is_archived ? <ArrowPathIcon className="h-3 w-3" aria-hidden="true" /> : <ArchiveBoxIcon className="h-3 w-3" aria-hidden="true" />}
                    {rt.is_archived ? 'Unarchive' : 'Archive'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Archive confirmation modal */}
      <Transition show={!!confirmArchive} as="div">
        <Dialog onClose={() => setConfirmArchive(null)} className="relative z-50">
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
                    {confirmArchive?.is_archived ? 'Unarchive Room Type' : 'Archive Room Type'}
                  </DialogTitle>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
                  Are you sure you want to {confirmArchive?.is_archived ? 'unarchive' : 'archive'} "{confirmArchive?.name}"?
                </p>
                <div className="flex items-center justify-end gap-3">
                  <button
                    onClick={() => setConfirmArchive(null)}
                    className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => confirmArchive && toggleArchive(confirmArchive)}
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
    </div>
  )
}
