import type { AxiosError } from 'axios'
import api from './api'
import type {
  Video,
  UploadVideoResponse,
  StartStreamResponse,
  ActiveStreamsResponse,
  VideosListResponse,
  VideoFilters,
  AnalysisStatusResponse,
} from '@/types/video'
import { MAX_VIDEO_SIZE_MB, SUPPORTED_VIDEO_MIME_TYPES, API_BASE_URL } from '@/utils/constants'

export const videoService = {
  async uploadVideo(
    file: File,
    cameraId?: string,
    onProgress?: (progress: number) => void
  ): Promise<Video> {
    // Validate file format
    if (!SUPPORTED_VIDEO_MIME_TYPES.includes(file.type)) {
      throw new Error('Invalid file format. Supported: MP4, AVI, MOV, MKV')
    }

    // Validate file size
    if (file.size > MAX_VIDEO_SIZE_MB * 1024 * 1024) {
      throw new Error(`File too large. Maximum size: ${MAX_VIDEO_SIZE_MB} MB`)
    }

    const formData = new FormData()
    formData.append('video', file)
    if (cameraId) {
      formData.append('camera_id', cameraId)
    }

    const config = {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent: any) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(progress)
        }
      },
    }

    const response = await api.post<UploadVideoResponse>('/videos/upload', formData, config)
    return response.data.video
  },

  async startStream(
    cameraId: string,
    streamUrl: string,
    name?: string
  ): Promise<StartStreamResponse> {
    if (!cameraId || !cameraId.trim()) {
      throw new Error('Camera ID is required')
    }
    if (!streamUrl || !streamUrl.trim()) {
      throw new Error('Stream URL is required')
    }

    // Optional: Validate RTSP URL format
    if (!streamUrl.startsWith('rtsp://') && !streamUrl.startsWith('http://')) {
      throw new Error('Invalid stream URL format. Must start with rtsp:// or http://')
    }

    const response = await api.post<StartStreamResponse>('/videos/start-stream', {
      camera_id: cameraId,
      stream_url: streamUrl,
      name,
    })
    return response.data
  },

  async stopStream(cameraId: string): Promise<void> {
    if (!cameraId || !cameraId.trim()) {
      throw new Error('Camera ID is required')
    }

    await api.post('/videos/stop-stream', { camera_id: cameraId })
  },

  async getActiveStreams(): Promise<ActiveStreamsResponse> {
    const response = await api.get<ActiveStreamsResponse>('/videos/streams/active')
    return response.data
  },

  async getVideos(
    page: number = 1,
    perPage: number = 20,
    filters?: VideoFilters
  ): Promise<VideosListResponse> {
    const params: any = {
      page,
      per_page: perPage,
    }

    if (filters) {
      if (filters.status) params.status = filters.status
      if (filters.camera_id) params.camera_id = filters.camera_id
      if (filters.upload_type) params.upload_type = filters.upload_type
      if (filters.date_from) params.date_from = filters.date_from
      if (filters.date_to) params.date_to = filters.date_to
      if (filters.analysis_result) params.analysis_result = filters.analysis_result
      if (filters.search) params.search = filters.search
    }

    const response = await api.get<VideosListResponse>('/videos', { params })
    return response.data
  },

  async getVideoDetails(videoId: string): Promise<Video> {
    const response = await api.get<{ video: Video }>(`/videos/${videoId}`)
    return response.data.video
  },

  async analyzeVideo(videoId: string): Promise<{ task_id: string }> {
    const response = await api.post<{ task_id: string }>(`/videos/${videoId}/analyze`)
    return response.data
  },

  async getAnalysisStatus(videoId: string): Promise<AnalysisStatusResponse> {
    const response = await api.get<AnalysisStatusResponse>(`/videos/${videoId}/analysis-status`)
    return response.data
  },

  async startLocalStream(cameraName?: string): Promise<{ stream_session_id: string; video_id: string }> {
    const response = await api.post<{
      message: string
      stream_session_id: string
      video_id: string
      status: string
    }>('/videos/start-local-stream', {
      camera_name: cameraName,
    })
    return {
      stream_session_id: response.data.stream_session_id,
      video_id: response.data.video_id,
    }
  },

  async stopLocalStream(streamSessionId: string): Promise<void> {
    await api.post('/videos/stop-local-stream', {
      stream_session_id: streamSessionId,
    })
  },

  async deleteVideo(videoId: string, reason?: string): Promise<void> {
    await api.delete(`/storage/videos/${videoId}`, { data: { reason } })
  },

  async downloadVideo(videoId: string): Promise<Blob> {
    const response = await api.get(`/storage/videos/${videoId}/download`, {
      responseType: 'blob',
    })
    return response.data
  },

  getThumbnailUrl(videoId: string): string {
    const baseUrl = API_BASE_URL.endsWith('/api') ? API_BASE_URL.replace('/api', '') : API_BASE_URL
    return `${baseUrl}/api/videos/${videoId}/thumbnail`
  },

  async getThumbnail(videoId: string): Promise<Blob> {
    const response = await api.get(`/videos/${videoId}/thumbnail`, {
      responseType: 'blob',
    })
    return response.data
  },
}

