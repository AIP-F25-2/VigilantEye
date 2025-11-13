import { useState, useRef, type DragEvent, type ChangeEvent } from 'react'
import { Upload, AlertCircle } from 'lucide-react'
import { cn } from '@/utils/cn'
import { SUPPORTED_VIDEO_MIME_TYPES, SUPPORTED_VIDEO_EXTENSIONS } from '@/utils/constants'

interface UploadZoneProps {
  onFileSelect: (file: File) => void
  accept: string
  maxSizeMB: number
  disabled?: boolean
  isUploading?: boolean
  uploadProgress?: number
}

export function UploadZone({
  onFileSelect,
  accept,
  maxSizeMB,
  disabled = false,
  isUploading = false,
  uploadProgress = 0,
}: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const validateFile = (file: File): boolean => {
    if (!file) {
      setError('Please select a file')
      return false
    }

    if (!SUPPORTED_VIDEO_MIME_TYPES.includes(file.type)) {
      setError(`Unsupported file type. Supported: ${SUPPORTED_VIDEO_EXTENSIONS.join(', ')}`)
      return false
    }

    if (file.size > maxSizeMB * 1024 * 1024) {
      setError(`File too large. Maximum size: ${maxSizeMB} MB`)
      return false
    }

    setError(null)
    return true
  }

  const handleDragEnter = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    if (!disabled && !isUploading) {
      setIsDragging(true)
    }
  }

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)

    if (disabled || isUploading) {
      return
    }

    const file = e.dataTransfer.files[0]
    if (file && validateFile(file)) {
      onFileSelect(file)
    }
  }

  const handleFileInput = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file && validateFile(file)) {
      onFileSelect(file)
    }
    e.target.value = ''
  }

  const handleClick = () => {
    if (!disabled && !isUploading) {
      fileInputRef.current?.click()
    }
  }

  return (
    <div
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      onClick={handleClick}
      className={cn(
        'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
        isDragging && !disabled && !isUploading
          ? 'border-primary-500 bg-primary-50'
          : error
          ? 'border-red-500 bg-red-50'
          : isUploading
          ? 'border-gray-400 bg-gray-100 cursor-not-allowed'
          : 'border-gray-300 bg-gray-50 hover:bg-gray-100',
        disabled && 'opacity-50 cursor-not-allowed'
      )}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept={SUPPORTED_VIDEO_EXTENSIONS.join(',')}
        onChange={handleFileInput}
        className="hidden"
        disabled={disabled || isUploading}
      />

      <Upload
        className={cn(
          'mx-auto h-12 w-12 mb-4',
          isDragging && !disabled && !isUploading
            ? 'text-primary-600'
            : error
            ? 'text-red-600'
            : 'text-gray-400'
        )}
      />

      <p className="text-lg font-medium text-gray-900 mb-2">
        Drag and drop video file here
      </p>
      <p className="text-sm text-gray-600 mb-4">or click to browse</p>

      <div className="text-xs text-gray-500 space-y-1">
        <p>Supported: {SUPPORTED_VIDEO_EXTENSIONS.join(', ').toUpperCase()}</p>
        <p>Maximum size: {maxSizeMB} MB</p>
      </div>

      {isUploading && (
        <div className="mt-4">
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div
              className="bg-primary-600 h-2.5 rounded-full transition-all"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
          <p className="text-sm text-gray-600 mt-2">{uploadProgress}% uploaded</p>
        </div>
      )}

      {error && (
        <p className="text-sm text-red-600 mt-2 flex items-center justify-center">
          <AlertCircle className="w-4 h-4 mr-1" />
          {error}
        </p>
      )}
    </div>
  )
}

