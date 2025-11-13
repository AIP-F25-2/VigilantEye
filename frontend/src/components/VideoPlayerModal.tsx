import { useState, useEffect, useRef, useCallback } from 'react'
import { X, Loader2, Download, BarChart3 } from 'lucide-react'
import { videoService } from '@/services/videoService'
import { Button } from '@/components/Button'
import { formatRelativeTime, formatDuration, formatBytes } from '@/utils/formatters'
import type { Video } from '@/types/video'
import toast from 'react-hot-toast'

interface VideoPlayerModalProps {
  video: Video | null
  onClose: () => void
  onAnalyze?: (videoId: string) => void
}

export function VideoPlayerModal({ video, onClose, onAnalyze }: VideoPlayerModalProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [videoUrl, setVideoUrl] = useState<string | null>(null)
  const videoRef = useRef<HTMLVideoElement>(null)

  // Extract fetch logic into a function
  const fetchVideo = useCallback(async () => {
    if (!video) return

    setIsLoading(true)
    setError(null)

    try {
      const blob = await videoService.downloadVideo(video.id)
      const url = URL.createObjectURL(blob)
      setVideoUrl((prevUrl) => {
        if (prevUrl) {
          URL.revokeObjectURL(prevUrl)
        }
        return url
      })
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || err.message || 'Failed to load video'
      setError(errorMessage)
      toast.error(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }, [video])

  // Fetch video when modal opens
  useEffect(() => {
    if (!video) {
      setVideoUrl((prevUrl) => {
        if (prevUrl) {
          URL.revokeObjectURL(prevUrl)
        }
        return null
      })
      setError(null)
      setIsLoading(false)
      return
    }

    fetchVideo()

    // Cleanup: revoke object URL when modal closes or video changes
    return () => {
      setVideoUrl((prevUrl) => {
        if (prevUrl) {
          URL.revokeObjectURL(prevUrl)
        }
        return null
      })
    }
  }, [video, fetchVideo])

  // Handle Escape key to close modal
  useEffect(() => {
    if (!video) return

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('keydown', handleEscape)
    }
  }, [video, onClose])

  if (!video) {
    return null
  }

  const handleDownload = async () => {
    try {
      const blob = await videoService.downloadVideo(video.id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = video.filename
      a.click()
      URL.revokeObjectURL(url)
      toast.success('Video download started')
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || err.message || 'Failed to download video'
      toast.error(errorMessage)
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-75 z-50 flex items-center justify-center p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div
        className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex-1 min-w-0">
            <h2 id="modal-title" className="text-xl font-semibold text-gray-900 truncate">
              {video.filename}
            </h2>
            <div className="mt-2 flex flex-wrap gap-4 text-sm text-gray-600">
              {video.duration && <span>Duration: {formatDuration(video.duration)}</span>}
              {video.resolution && <span>Resolution: {video.resolution}</span>}
              {video.filesize && <span>Size: {formatBytes(video.filesize)}</span>}
              <span>Uploaded: {formatRelativeTime(video.created_at)}</span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="ml-4 text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500 rounded"
            aria-label="Close modal"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6">
          {isLoading && (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="h-12 w-12 text-primary-600 animate-spin mb-4" />
              <p className="text-gray-600">Loading video...</p>
            </div>
          )}

          {error && (
            <div className="flex flex-col items-center justify-center py-12">
              <p className="text-red-600 mb-4">{error}</p>
              <Button onClick={() => { setError(null); fetchVideo(); }}>Retry</Button>
            </div>
          )}

          {videoUrl && !isLoading && !error && (
            <div className="space-y-4">
              <video
                ref={videoRef}
                src={videoUrl}
                controls
                className="w-full rounded-lg"
                preload="metadata"
              />
              <div className="flex gap-2">
                <Button onClick={handleDownload} variant="secondary">
                  <Download className="mr-2 h-4 w-4" />
                  Download
                </Button>
                {onAnalyze && video.status === 'ready' && !video.analysis_result && (
                  <Button
                    onClick={() => {
                      onAnalyze(video.id)
                      onClose()
                    }}
                    variant="primary"
                  >
                    <BarChart3 className="mr-2 h-4 w-4" />
                    Analyze Video
                  </Button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

