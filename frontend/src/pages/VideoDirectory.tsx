import { useState, useEffect, useCallback, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Play,
  Trash2,
  BarChart3,
  Download,
  Grid,
  List,
  RefreshCw,
  Video as VideoIcon,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '@/hooks/useAuth'
import { useWebSocket } from '@/hooks/useWebSocket'
import { videoService } from '@/services/videoService'
import { Button } from '@/components/Button'
import { VideoStatusBadge } from '@/components/VideoStatusBadge'
import { AnalysisResultBadge } from '@/components/AnalysisResultBadge'
import { TTLCountdown } from '@/components/TTLCountdown'
import { VideoPlayerModal } from '@/components/VideoPlayerModal'
import { DeleteConfirmDialog } from '@/components/DeleteConfirmDialog'
import { FilterBar } from '@/components/FilterBar'
import { RoleGuard } from '@/components/RoleGuard'
import { formatRelativeTime, formatDuration, truncateFilename } from '@/utils/formatters'
import { WS_NAMESPACE_ANALYSIS } from '@/utils/constants'
import type { Video, VideoFilters, ViewMode, AnalysisCompleteEvent } from '@/types/video'
import type { AxiosError } from 'axios'

export default function VideoDirectoryPage() {
  const { user, isAdmin } = useAuth()
  const { socket } = useWebSocket(WS_NAMESPACE_ANALYSIS)
  const queryClient = useQueryClient()

  // State
  const [viewMode, setViewMode] = useState<ViewMode>('table')
  const [page, setPage] = useState(1)
  const perPage = 20
  const [filters, setFilters] = useState<VideoFilters>({})
  const [selectedVideo, setSelectedVideo] = useState<Video | null>(null)
  const [videoToDelete, setVideoToDelete] = useState<Video | null>(null)
  const [analyzingVideoId, setAnalyzingVideoId] = useState<string | null>(null)
  const [thumbnailUrls, setThumbnailUrls] = useState<Record<string, string>>({})

  // Compute stable query key
  const filtersKey = useMemo(() => {
    return JSON.stringify({
      status: filters.status || '',
      camera_id: filters.camera_id || '',
      upload_type: filters.upload_type || '',
      date_from: filters.date_from || '',
      date_to: filters.date_to || '',
      analysis_result: filters.analysis_result || '',
      search: filters.search || '',
    })
  }, [filters])

  // React Query: Fetch Videos
  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['videos', page, filtersKey],
    queryFn: () => videoService.getVideos(page, perPage, filters),
    keepPreviousData: true,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  const allVideos = data?.videos || []
  const pagination = data?.pagination

  // Client-side search filtering if backend doesn't support it
  const videos = useMemo(() => {
    if (!filters.search || filters.search.trim() === '') {
      return allVideos
    }
    const searchLower = filters.search.toLowerCase()
    return allVideos.filter((video) =>
      video.filename.toLowerCase().includes(searchLower)
    )
  }, [allVideos, filters.search])

  // Extract unique cameras from videos for filter dropdown - maintain across pages
  const [allSeenCameras, setAllSeenCameras] = useState<Set<string>>(new Set())
  
  useEffect(() => {
    setAllSeenCameras((prev) => {
      const cameras = new Set(prev)
      videos.forEach((video) => {
        if (video.camera_id) {
          cameras.add(video.camera_id)
        }
      })
      // Only update if there are new cameras
      if (cameras.size !== prev.size || Array.from(cameras).some(c => !prev.has(c))) {
        return cameras
      }
      return prev
    })
  }, [videos])

  const availableCameras = useMemo(() => {
    return Array.from(allSeenCameras)
  }, [allSeenCameras])

  // React Query: Delete Mutation
  const deleteMutation = useMutation({
    mutationFn: ({ videoId, reason }: { videoId: string; reason?: string }) =>
      videoService.deleteVideo(videoId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries(['videos'])
      toast.success('Video deleted successfully')
      setVideoToDelete(null)
    },
    onError: (error: AxiosError) => {
      const errorMessage =
        (error.response?.data as any)?.error || error.message || 'Failed to delete video'
      toast.error(errorMessage)
    },
  })

  // React Query: Analyze Mutation
  const analyzeMutation = useMutation({
    mutationFn: (videoId: string) => videoService.analyzeVideo(videoId),
    onMutate: (videoId: string) => {
      setAnalyzingVideoId(videoId)
      // Optimistic update: set status to analyzing
      queryClient.setQueryData(['videos', page, filtersKey], (old: any) => {
        if (!old) return old
        return {
          ...old,
          videos: old.videos.map((v: Video) =>
            v.id === videoId ? { ...v, status: 'analyzing' as const } : v
          ),
        }
      })
    },
    onSuccess: () => {
      toast.success('Analysis started')
      setAnalyzingVideoId(null)
    },
    onError: (error: AxiosError, videoId: string) => {
      setAnalyzingVideoId(null)
      // Rollback optimistic update on error
      queryClient.setQueryData(['videos', page, filtersKey], (old: any) => {
        if (!old) return old
        return {
          ...old,
          videos: old.videos.map((v: Video) =>
            v.id === videoId ? { ...v, status: 'ready' as const } : v
          ),
        }
      })
      const errorMessage =
        (error.response?.data as any)?.error || error.message || 'Failed to start analysis'
      toast.error(errorMessage)
    },
  })

  // Load thumbnails with proper auth
  const videoIdsString = useMemo(() => videos.map((v) => v.id).sort().join(','), [videos])
  
  useEffect(() => {
    if (!videoIdsString) return

    const loadThumbnails = async () => {
      const videosToLoad = videos.filter((video) => !thumbnailUrls[video.id])
      if (videosToLoad.length === 0) return

      const newThumbnailUrls: Record<string, string> = {}
      const promises = videosToLoad.map(async (video) => {
        try {
          const blob = await videoService.getThumbnail(video.id)
          const url = URL.createObjectURL(blob)
          newThumbnailUrls[video.id] = url
        } catch (error) {
          // Silently fail - will show placeholder
        }
      })
      await Promise.all(promises)
      
      if (Object.keys(newThumbnailUrls).length > 0) {
        setThumbnailUrls((prev) => ({ ...prev, ...newThumbnailUrls }))
      }
    }

    loadThumbnails()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [videoIdsString])

  // Cleanup: revoke URLs on unmount
  useEffect(() => {
    return () => {
      Object.values(thumbnailUrls).forEach((url) => {
        URL.revokeObjectURL(url)
      })
    }
  }, [])

  // WebSocket: Real-Time Updates
  useEffect(() => {
    if (!socket) return

    const handleAnalysisComplete = (data: AnalysisCompleteEvent) => {
      // Update specific video in cache
      queryClient.setQueryData(['videos', page, filtersKey], (old: any) => {
        if (!old) return old
        return {
          ...old,
          videos: old.videos.map((v: Video) =>
            v.id === data.video_id
              ? {
                  ...v,
                  status: 'analyzed' as const,
                  analysis_result: data.result,
                  analysis_completed_at: data.timestamp,
                }
              : v
          ),
        }
      })

      if (data.result === 'suspicious') {
        const ticketId = data.ticket_id?.substring(0, 8) || 'N/A'
        toast.error(`🚨 Suspicious activity detected! Ticket #${ticketId}`, {
          duration: 6000,
        })
      } else {
        toast.success('✅ No suspicious activity detected', {
          duration: 4000,
        })
      }
    }

    socket.on('analysis_complete', handleAnalysisComplete)

    return () => {
      socket.off('analysis_complete', handleAnalysisComplete)
    }
  }, [socket, queryClient, page, filtersKey])

  // Action Handlers
  const handlePlay = useCallback((video: Video) => {
    setSelectedVideo(video)
  }, [])

  const handleDelete = useCallback((video: Video) => {
    setVideoToDelete(video)
  }, [])

  const handleAnalyze = useCallback(
    (video: Video) => {
      analyzeMutation.mutate(video.id)
    },
    [analyzeMutation]
  )

  const handleDownload = useCallback(async (video: Video) => {
    try {
      const blob = await videoService.downloadVideo(video.id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = video.filename
      a.click()
      URL.revokeObjectURL(url)
      toast.success('Video download started')
    } catch (error: any) {
      const errorMessage =
        error.response?.data?.error || error.message || 'Failed to download video'
      toast.error(errorMessage)
    }
  }, [])

  // Filter Handlers
  const handleFiltersChange = useCallback(
    (newFilters: VideoFilters) => {
      setFilters(newFilters)
      setPage(1) // Reset to page 1 when filters change
    },
    []
  )

  const handleResetFilters = useCallback(() => {
    setFilters({})
    setPage(1)
  }, [])

  // Pagination Handlers
  const handlePageChange = useCallback((newPage: number) => {
    setPage(newPage)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])

  const renderPagination = () => {
    if (!pagination || pagination.pages <= 1) return null

    const { page: currentPage, pages, total } = pagination
    const start = (currentPage - 1) * perPage + 1
    const end = Math.min(currentPage * perPage, total)

    // Calculate page numbers to show
    const getPageNumbers = () => {
      const delta = 2
      const range = []
      const rangeWithDots = []

      for (
        let i = Math.max(2, currentPage - delta);
        i <= Math.min(pages - 1, currentPage + delta);
        i++
      ) {
        range.push(i)
      }

      if (currentPage - delta > 2) {
        rangeWithDots.push(1, '...')
      } else {
        rangeWithDots.push(1)
      }

      rangeWithDots.push(...range)

      if (currentPage + delta < pages - 1) {
        rangeWithDots.push('...', pages)
      } else if (pages > 1) {
        rangeWithDots.push(pages)
      }

      return rangeWithDots
    }

    const pageNumbers = getPageNumbers()

    return (
      <div className="flex items-center justify-between mt-6">
        <div className="text-sm text-gray-700">
          Showing <span className="font-medium">{start}</span> to{' '}
          <span className="font-medium">{end}</span> of{' '}
          <span className="font-medium">{total}</span> videos
        </div>
        <div className="flex items-center gap-2">
          <Button
            onClick={() => handlePageChange(currentPage - 1)}
            disabled={currentPage === 1}
            variant="secondary"
            size="sm"
          >
            <ChevronLeft className="h-4 w-4" />
            Previous
          </Button>
          <div className="flex gap-1">
            {pageNumbers.map((pageNum, idx) => {
              if (pageNum === '...') {
                return (
                  <span key={`ellipsis-${idx}`} className="px-3 py-2 text-gray-500">
                    ...
                  </span>
                )
              }
              const pageNumber = pageNum as number
              return (
                <button
                  key={pageNumber}
                  onClick={() => handlePageChange(pageNumber)}
                  className={`px-3 py-2 text-sm font-medium rounded-md ${
                    pageNumber === currentPage
                      ? 'bg-primary-600 text-white'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  {pageNumber}
                </button>
              )
            })}
          </div>
          <Button
            onClick={() => handlePageChange(currentPage + 1)}
            disabled={currentPage >= pages}
            variant="secondary"
            size="sm"
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    )
  }

  // Table View
  const renderTableView = () => {
    if (isLoading) {
      return (
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          <div className="animate-pulse space-y-4 p-6">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-16 bg-gray-200 rounded" />
            ))}
          </div>
        </div>
      )
    }

    if (isError) {
      return (
        <div className="bg-white rounded-lg shadow-md p-6 text-center">
          <p className="text-red-600 mb-4">
            {(error as AxiosError)?.response?.data
              ? ((error as AxiosError).response?.data as any)?.error
              : 'Failed to load videos'}
          </p>
          <Button onClick={() => refetch()} variant="primary">
            Retry
          </Button>
        </div>
      )
    }

    if (videos.length === 0) {
      return (
        <div className="bg-white rounded-lg shadow-md p-12 text-center">
          <VideoIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 mb-4">No videos found</p>
          {Object.keys(filters).length > 0 ? (
            <Button onClick={handleResetFilters} variant="primary">
              Reset Filters
            </Button>
          ) : (
            <p className="text-sm text-gray-500">Upload your first video to get started</p>
          )}
        </div>
      )
    }

    return (
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Thumbnail
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Filename
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Upload Time
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider hidden md:table-cell">
                  Duration
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Analysis
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  TTL
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {videos.map((video) => (
                <tr
                  key={video.id}
                  className="hover:bg-gray-50 transition-colors cursor-pointer"
                  onClick={() => handlePlay(video)}
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <img
                      src={thumbnailUrls[video.id] || 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="112" height="64" viewBox="0 0 112 64"%3E%3Crect fill="%23e5e7eb" width="112" height="64"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" fill="%239ca3af" font-size="12"%3ENo Image%3C/text%3E%3C/svg%3E'}
                      alt={video.filename}
                      className="h-16 w-28 object-cover rounded"
                      loading="lazy"
                      onError={(e) => {
                        ;(e.target as HTMLImageElement).src =
                          'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="112" height="64" viewBox="0 0 112 64"%3E%3Crect fill="%23e5e7eb" width="112" height="64"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" fill="%239ca3af" font-size="12"%3ENo Image%3C/text%3E%3C/svg%3E'
                      }}
                    />
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900">
                      {truncateFilename(video.filename, 30)}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatRelativeTime(video.created_at)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 hidden md:table-cell">
                    {video.duration ? formatDuration(video.duration) : 'N/A'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <VideoStatusBadge status={video.status} />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <AnalysisResultBadge result={video.analysis_result} />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <TTLCountdown expiresAt={video.expires_at} />
                  </td>
                  <td
                    className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        onClick={() => handlePlay(video)}
                        variant="ghost"
                        size="sm"
                        title="Play video"
                      >
                        <Play className="h-4 w-4" />
                      </Button>
                      {video.status === 'ready' && !video.analysis_result && (
                        <Button
                          onClick={() => handleAnalyze(video)}
                          variant="ghost"
                          size="sm"
                          disabled={analyzingVideoId === video.id}
                          title="Analyze video"
                        >
                          <BarChart3 className="h-4 w-4" />
                        </Button>
                      )}
                      <RoleGuard role="admin">
                        <Button
                          onClick={() => handleDelete(video)}
                          variant="ghost"
                          size="sm"
                          title="Delete video"
                        >
                          <Trash2 className="h-4 w-4 text-red-600" />
                        </Button>
                      </RoleGuard>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  // Grid View
  const renderGridView = () => {
    if (isLoading) {
      return (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <div key={i} className="bg-white rounded-lg shadow-md overflow-hidden animate-pulse">
              <div className="h-48 bg-gray-200" />
              <div className="p-4 space-y-2">
                <div className="h-4 bg-gray-200 rounded w-3/4" />
                <div className="h-4 bg-gray-200 rounded w-1/2" />
              </div>
            </div>
          ))}
        </div>
      )
    }

    if (isError || videos.length === 0) {
      return renderTableView() // Reuse table view empty/error states
    }

    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {videos.map((video) => (
          <div
            key={video.id}
            className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow cursor-pointer"
            onClick={() => handlePlay(video)}
          >
            <div className="relative">
              <img
                src={thumbnailUrls[video.id] || 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="192" viewBox="0 0 400 192"%3E%3Crect fill="%23e5e7eb" width="400" height="192"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" fill="%239ca3af" font-size="16"%3ENo Image%3C/text%3E%3C/svg%3E'}
                alt={video.filename}
                className="w-full h-48 object-cover"
                loading="lazy"
                onError={(e) => {
                  ;(e.target as HTMLImageElement).src =
                    'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="192" viewBox="0 0 400 192"%3E%3Crect fill="%23e5e7eb" width="400" height="192"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" fill="%239ca3af" font-size="16"%3ENo Image%3C/text%3E%3C/svg%3E'
                }}
              />
              <div className="absolute top-2 right-2">
                <VideoStatusBadge status={video.status} />
              </div>
            </div>
            <div className="p-4">
              <h3 className="text-sm font-medium text-gray-900 mb-2 truncate">
                {truncateFilename(video.filename, 25)}
              </h3>
              <div className="flex items-center justify-between mb-2">
                <AnalysisResultBadge result={video.analysis_result} />
                <TTLCountdown expiresAt={video.expires_at} />
              </div>
              <p className="text-xs text-gray-500 mb-3">{formatRelativeTime(video.created_at)}</p>
              <div
                className="flex items-center gap-2"
                onClick={(e) => e.stopPropagation()}
              >
                <Button
                  onClick={() => handlePlay(video)}
                  variant="ghost"
                  size="sm"
                  className="flex-1"
                >
                  <Play className="h-4 w-4 mr-1" />
                  Play
                </Button>
                {video.status === 'ready' && !video.analysis_result && (
                  <Button
                    onClick={() => handleAnalyze(video)}
                    variant="ghost"
                    size="sm"
                    disabled={analyzingVideoId === video.id}
                  >
                    <BarChart3 className="h-4 w-4" />
                  </Button>
                )}
                <RoleGuard role="admin">
                  <Button
                    onClick={() => handleDelete(video)}
                    variant="ghost"
                    size="sm"
                  >
                    <Trash2 className="h-4 w-4 text-red-600" />
                  </Button>
                </RoleGuard>
              </div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      {/* Page Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center mb-2">
            <VideoIcon className="h-8 w-8 text-primary-600 mr-2" />
            <h1 className="text-3xl font-bold text-gray-900">Video Directory</h1>
          </div>
          <p className="text-gray-600">Manage and analyze your surveillance videos</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-white rounded-lg shadow-sm p-2">
            <Button
              onClick={() => setViewMode('table')}
              variant={viewMode === 'table' ? 'primary' : 'ghost'}
              size="sm"
            >
              <List className="h-4 w-4" />
            </Button>
            <Button
              onClick={() => setViewMode('grid')}
              variant={viewMode === 'grid' ? 'primary' : 'ghost'}
              size="sm"
            >
              <Grid className="h-4 w-4" />
            </Button>
          </div>
          <Button onClick={() => refetch()} variant="secondary" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Filter Bar */}
      <FilterBar
        filters={filters}
        onFiltersChange={handleFiltersChange}
        onReset={handleResetFilters}
        availableCameras={availableCameras}
      />

      {/* Video List */}
      {viewMode === 'table' ? renderTableView() : renderGridView()}

      {/* Pagination */}
      {renderPagination()}

      {/* Modals */}
      <VideoPlayerModal
        video={selectedVideo}
        onClose={() => setSelectedVideo(null)}
        onAnalyze={handleAnalyze}
      />
      <DeleteConfirmDialog
        video={videoToDelete}
        onConfirm={(reason) => {
          if (videoToDelete) {
            deleteMutation.mutate({ videoId: videoToDelete.id, reason })
          }
        }}
        onCancel={() => setVideoToDelete(null)}
        isDeleting={deleteMutation.isLoading}
      />
    </div>
  )
}

