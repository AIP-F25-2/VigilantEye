import { useState } from 'react'
import { Image, Headphones, X, ChevronLeft, ChevronRight } from 'lucide-react'
import { formatRelativeTime } from '@/utils/formatters'
import type { Evidence } from '@/types/ticket'

interface EvidenceGalleryProps {
  evidence: Evidence[]
  ticketId: string
}

export function EvidenceGallery({ evidence, ticketId }: EvidenceGalleryProps) {
  const [selectedImage, setSelectedImage] = useState<Evidence | null>(null)
  const [isLoadingImage, setIsLoadingImage] = useState(false)

  const frames = evidence.filter((e) => e.type === 'frame')
  const audioFiles = evidence.filter((e) => e.type === 'audio')
  const videos = evidence.filter((e) => e.type === 'video')

  const handleImageClick = (frame: Evidence) => {
    setSelectedImage(frame)
    setIsLoadingImage(true)
  }

  const handleCloseLightbox = () => {
    setSelectedImage(null)
    setIsLoadingImage(false)
  }

  const handlePrevious = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (!selectedImage) return
    const currentIndex = frames.findIndex((f) => f.id === selectedImage.id)
    if (currentIndex > 0) {
      setSelectedImage(frames[currentIndex - 1])
    }
  }

  const handleNext = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (!selectedImage) return
    const currentIndex = frames.findIndex((f) => f.id === selectedImage.id)
    if (currentIndex < frames.length - 1) {
      setSelectedImage(frames[currentIndex + 1])
    }
  }

  // Handle Escape key for lightbox
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && selectedImage) {
      handleCloseLightbox()
    }
  }

  return (
    <div className="space-y-8" onKeyDown={handleKeyDown} tabIndex={0}>
      {/* Frame Evidence Section */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Image className="h-5 w-5 text-gray-600" />
          <h3 className="text-lg font-semibold text-gray-900">
            Frame Evidence ({frames.length})
          </h3>
        </div>
        {frames.length === 0 ? (
          <p className="text-gray-500 text-sm">No frame evidence</p>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {frames.map((frame) => (
              <div key={frame.id} className="space-y-2">
                <div className="relative group">
                  <img
                    src={`/api/storage/evidence/${frame.id}/download`}
                    alt={frame.description || `Frame ${frame.frame_number || frame.id}`}
                    className="w-full h-32 object-cover rounded cursor-pointer hover:opacity-80 transition-opacity"
                    onClick={() => handleImageClick(frame)}
                    loading="lazy"
                  />
                </div>
                <div className="text-xs text-gray-600 space-y-1">
                  {frame.frame_number && (
                    <p className="font-medium">Frame #{frame.frame_number}</p>
                  )}
                  {frame.timestamp && (
                    <p className="text-gray-500">
                      {formatRelativeTime(new Date(frame.timestamp * 1000).toISOString())}
                    </p>
                  )}
                  {frame.description && (
                    <p className="truncate" title={frame.description}>
                      {frame.description.length > 50
                        ? `${frame.description.substring(0, 50)}...`
                        : frame.description}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Audio Evidence Section */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Headphones className="h-5 w-5 text-gray-600" />
          <h3 className="text-lg font-semibold text-gray-900">
            Audio Evidence ({audioFiles.length})
          </h3>
        </div>
        {audioFiles.length === 0 ? (
          <p className="text-gray-500 text-sm">No audio evidence</p>
        ) : (
          <div className="space-y-4">
            {audioFiles.map((audio) => (
              <div key={audio.id} className="bg-gray-50 rounded-lg p-4 space-y-2">
                <audio controls className="w-full" preload="none">
                  <source
                    src={`/api/storage/evidence/${audio.id}/download`}
                    type="audio/wav"
                  />
                  Your browser does not support the audio element.
                </audio>
                <div className="text-sm text-gray-600 space-y-1">
                  {audio.timestamp && (
                    <p>
                      <span className="font-medium">Timestamp:</span>{' '}
                      {formatRelativeTime(new Date(audio.timestamp * 1000).toISOString())}
                    </p>
                  )}
                  {audio.description && (
                    <p>
                      <span className="font-medium">Description:</span> {audio.description}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Video Evidence Section */}
      {videos.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Video Evidence ({videos.length})
          </h3>
          <div className="space-y-4">
            {videos.map((video) => (
              <div key={video.id} className="bg-gray-50 rounded-lg p-4">
                <video controls className="w-full rounded" preload="metadata">
                  <source
                    src={`/api/storage/evidence/${video.id}/download`}
                    type="video/mp4"
                  />
                  Your browser does not support the video element.
                </video>
                {video.description && (
                  <p className="mt-2 text-sm text-gray-600">{video.description}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Lightbox for Full-Size Images */}
      {selectedImage && (
        <div
          className="fixed inset-0 bg-black bg-opacity-90 z-50 flex items-center justify-center p-4"
          onClick={handleCloseLightbox}
        >
          <div className="relative max-w-7xl w-full max-h-[90vh] flex items-center justify-center">
            <button
              onClick={handleCloseLightbox}
              className="absolute top-4 right-4 text-white hover:text-gray-300 z-10"
              aria-label="Close lightbox"
            >
              <X className="h-8 w-8" />
            </button>
            {frames.length > 1 && (
              <>
                <button
                  onClick={handlePrevious}
                  className="absolute left-4 text-white hover:text-gray-300 z-10 bg-black bg-opacity-50 rounded-full p-2"
                  aria-label="Previous image"
                >
                  <ChevronLeft className="h-6 w-6" />
                </button>
                <button
                  onClick={handleNext}
                  className="absolute right-4 text-white hover:text-gray-300 z-10 bg-black bg-opacity-50 rounded-full p-2"
                  aria-label="Next image"
                >
                  <ChevronRight className="h-6 w-6" />
                </button>
              </>
            )}
            <img
              src={`/api/storage/evidence/${selectedImage.id}/download`}
              alt={selectedImage.description || 'Evidence image'}
              className="max-w-full max-h-[80vh] object-contain"
              onLoad={() => setIsLoadingImage(false)}
            />
            {selectedImage.description && (
              <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-black bg-opacity-75 text-white px-4 py-2 rounded text-sm max-w-2xl">
                {selectedImage.description}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

