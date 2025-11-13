export interface Video {
  id: string
  filename: string
  filepath: string
  camera_id: string | null
  upload_type: 'upload' | 'stream'
  user_id: string
  filesize: number | null
  duration: number | null
  fps: number | null
  resolution: string | null
  status: 'uploading' | 'processing' | 'ready' | 'analyzing' | 'analyzed' | 'error'
  analysis_result: 'clean' | 'suspicious' | null
  created_at: string
  expires_at: string
  analysis_completed_at: string | null
}

export interface Stream {
  camera_id: string
  camera_name: string
  stream_url: string
  video_id: string
  started_at: string
}

export interface UploadVideoResponse {
  message: string
  video: Video
}

export interface StartStreamResponse {
  message: string
  camera_id: string
  video_id: string
  status: string
}

export interface ActiveStreamsResponse {
  active_streams: Stream[]
  count: number
  max_streams: number
}

export interface AnalysisCompleteEvent {
  video_id: string
  result: 'suspicious' | 'clean'
  ticket_id: string | null
  threat_level: 'low' | 'medium' | 'high' | 'critical' | null
  timestamp: string
}

export interface VideoFilters {
  status?: string
  camera_id?: string
  upload_type?: 'upload' | 'stream'
  date_from?: string
  date_to?: string
  search?: string
  analysis_result?: 'clean' | 'suspicious' | 'pending'
}

export interface PaginationInfo {
  page: number
  per_page: number
  total: number
  pages: number
}

export interface VideosListResponse {
  videos: Video[]
  pagination: PaginationInfo
}

export interface AnalysisStatusResponse {
  status: 'pending' | 'processing' | 'completed' | 'error'
  analysis_result: 'clean' | 'suspicious' | null
  ticket_id: string | null
  analyzed_at: string | null
}

export interface LocalStreamSession {
  session_id: string
  video_id: string
  started_at: string
}

export type ViewMode = 'table' | 'grid'

