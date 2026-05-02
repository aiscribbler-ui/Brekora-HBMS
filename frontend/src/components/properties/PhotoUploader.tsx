import { useCallback, useState, useRef } from 'react'
import { PhotoIcon, XMarkIcon, CloudArrowUpIcon } from '@heroicons/react/24/outline'

export interface PhotoFile {
  file: File
  preview: string
}

interface PhotoUploaderProps {
  photos: PhotoFile[]
  onChange: (photos: PhotoFile[]) => void
  onUpload?: () => void
  disabled?: boolean
}

export default function PhotoUploader({ photos, onChange, onUpload, disabled }: PhotoUploaderProps) {
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList) return
      const newPhotos: PhotoFile[] = []
      Array.from(fileList).forEach((file) => {
        if (!file.type.startsWith('image/')) return
        const reader = new FileReader()
        reader.onloadend = () => {
          newPhotos.push({ file, preview: reader.result as string })
          if (newPhotos.length === Array.from(fileList).filter((f) => f.type.startsWith('image/')).length) {
            onChange([...photos, ...newPhotos])
          }
        }
        reader.readAsDataURL(file)
      })
    },
    [photos, onChange],
  )

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      handleFiles(e.dataTransfer.files)
    },
    [handleFiles],
  )

  const removePhoto = useCallback(
    (index: number) => {
      const updated = [...photos]
      updated.splice(index, 1)
      onChange(updated)
    },
    [photos, onChange],
  )

  return (
    <div className="space-y-3">
      <div
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={[
          'border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors',
          isDragging ? 'border-brand-500 bg-brand-50' : 'border-gray-300 hover:border-brand-400 bg-white',
          disabled ? 'opacity-50 cursor-not-allowed' : '',
        ].join(' ')}
        role="button"
        aria-label="Upload photos"
      >
        <CloudArrowUpIcon className="mx-auto h-10 w-10 text-gray-400" />
        <p className="mt-2 text-sm text-gray-600">
          <span className="font-medium text-brand-600">Click to upload</span> or drag and drop
        </p>
        <p className="mt-1 text-xs text-gray-500">PNG, JPG, GIF up to 10MB</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept="image/*"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
          disabled={disabled}
        />
      </div>

      {photos.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
          {photos.map((photo, idx) => (
            <div key={idx} className="relative group rounded-lg overflow-hidden border border-gray-200">
              <img
                src={photo.preview}
                alt={`Preview ${idx + 1}`}
                className="h-24 w-full object-cover"
              />
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  removePhoto(idx)
                }}
                className="absolute top-1 right-1 bg-gray-900/70 text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                aria-label={`Remove photo ${idx + 1}`}
              >
                <XMarkIcon className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      {onUpload && photos.length > 0 && (
        <button
          type="button"
          onClick={onUpload}
          disabled={disabled}
          className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-md hover:bg-brand-700 disabled:opacity-50 transition-colors"
        >
          <PhotoIcon className="h-4 w-4" />
          Upload {photos.length} photo{photos.length !== 1 ? 's' : ''}
        </button>
      )}
    </div>
  )
}
