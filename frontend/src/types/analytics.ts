export interface HealthResponse {
  status: 'healthy' | 'unhealthy'
  database: {
    status: 'connected' | 'disconnected'
    response_time_ms: number
  }
  redis: {
    status: 'connected' | 'disconnected'
    response_time_ms: number
  }
  chromadb: {
    status: 'connected' | 'disconnected'
    response_time_ms: number
  }
  celery: {
    status: 'running' | 'stopped'
    workers: number
    active_tasks: number
  }
  storage: {
    total_bytes: number
    used_bytes: number
    free_bytes: number
    percentage: number
  }
  timestamp: string
}

export interface ReadinessResponse {
  ready: boolean
  checks: Array<{
    name: string
    status: 'pass' | 'fail'
    message?: string
  }>
}

export interface MetricsResponse {
  api_latency: {
    p50: number
    p95: number
    p99: number
  }
  ai_inference_times: {
    person_detection: number
    scene_analysis: number
    object_detection: number
    speech_to_text: number
    audio_classification: number
    llm_analysis: number
  }
  database_pool: {
    size: number
    checked_out: number
    overflow: number
    checked_in: number
  }
  storage_usage: {
    videos: number
    frames: number
    audio: number
    evidence: number
    total: number
  }
  timestamp: string
}

export interface TicketAnalytics {
  tickets_over_time: Array<{
    timestamp: string
    count: number
  }>
  threat_distribution: Array<{
    threat_level: string
    count: number
    percentage: number
  }>
  response_times: {
    avg_response_time: number
    avg_resolution_time: number
    p50: number
    p95: number
    p99: number
  }
  top_cameras: Array<{
    camera_id: string
    camera_name: string
    incident_count: number
  }>
  total_tickets: number
  open_tickets: number
  sla_breach_rate: number
}

export interface ChartDataPoint {
  name: string
  value: number
  [key: string]: any
}

export interface DateRange {
  from: Date | string
  to: Date | string
}

export type HealthStatus = 'healthy' | 'warning' | 'error'

