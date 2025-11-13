import { useState, useEffect } from 'react'
import { AlertTriangle, X } from 'lucide-react'
import { Button } from '@/components/Button'
import { formatRelativeTime, formatDuration, formatBytes } from '@/utils/formatters'
import type { Video } from '@/types/video'

interface DeleteConfirmDialogProps {
  video: Video | null
  onConfirm: (reason?: string) => void
  onCancel: () => void
  isDeleting: boolean
}

export function DeleteConfirmDialog({
  video,
  onConfirm,
  onCancel,
  isDeleting,
}: DeleteConfirmDialogProps) {
  const [reason, setReason] = useState('')

  // Reset reason when video changes
  useEffect(() => {
    setReason('')
  }, [video])

  // Handle Escape key
  useEffect(() => {
    if (!video) return

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isDeleting) {
        onCancel()
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('keydown', handleEscape)
    }
  }, [video, onCancel, isDeleting])

  if (!video) {
    return null
  }

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-75 z-50 flex items-center justify-center p-4"
      onClick={onCancel}
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="dialog-title"
    >
      <div
        className="bg-white rounded-lg max-w-md w-full"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center">
            <AlertTriangle className="h-6 w-6 text-red-600 mr-3" />
            <h2 id="dialog-title" className="text-xl font-semibold text-gray-900">
              Delete Video?
            </h2>
          </div>
          <button
            onClick={onCancel}
            disabled={isDeleting}
            className="text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500 rounded"
            aria-label="Close dialog"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4">
          <p className="text-gray-600">This action cannot be undone.</p>

          {/* Video Details */}
          <div className="bg-gray-50 rounded-md p-4 space-y-2">
            <p className="text-sm font-medium text-gray-900">Video Details:</p>
            <div className="text-sm text-gray-600 space-y-1">
              <p>
                <span className="font-medium">Filename:</span> {video.filename}
              </p>
              <p>
                <span className="font-medium">Uploaded:</span> {formatRelativeTime(video.created_at)}
              </p>
              {video.duration && (
                <p>
                  <span className="font-medium">Duration:</span> {formatDuration(video.duration)}
                </p>
              )}
              {video.filesize && (
                <p>
                  <span className="font-medium">Size:</span> {formatBytes(video.filesize)}
                </p>
              )}
            </div>
          </div>

          <p className="text-sm text-gray-600">
            This video will be permanently deleted from storage.
          </p>

          {/* Reason Input */}
          <div>
            <label htmlFor="delete-reason" className="block text-sm font-medium text-gray-700 mb-1">
              Reason for deletion (optional)
            </label>
            <textarea
              id="delete-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g., Duplicate upload, test video, etc."
              maxLength={500}
              disabled={isDeleting}
              rows={3}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm disabled:bg-gray-100 disabled:cursor-not-allowed px-3 py-2 border"
            />
            <p className="mt-1 text-xs text-gray-500">{reason.length}/500 characters</p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200">
          <Button onClick={onCancel} variant="secondary" disabled={isDeleting}>
            Cancel
          </Button>
          <Button
            onClick={() => onConfirm(reason || undefined)}
            variant="danger"
            isLoading={isDeleting}
            disabled={isDeleting}
          >
            Delete Video
          </Button>
        </div>
      </div>
    </div>
  )
}

