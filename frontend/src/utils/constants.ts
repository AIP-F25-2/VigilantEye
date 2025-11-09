export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api'

export const USER_ROLES = {
  STAFF: 'staff',
  ADMIN: 'admin',
} as const

export const TICKET_STATUS = {
  OPEN: 'open',
  ACKNOWLEDGED: 'acknowledged',
  IN_PROGRESS: 'in_progress',
  RESOLVED: 'resolved',
  CLOSED: 'closed',
} as const

export const TICKET_PRIORITY = {
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
  CRITICAL: 'critical',
} as const

export const THREAT_LEVEL = {
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
  CRITICAL: 'critical',
} as const

export const VIDEO_STATUS = {
  UPLOADING: 'uploading',
  PROCESSING: 'processing',
  READY: 'ready',
  ANALYZING: 'analyzing',
  ANALYZED: 'analyzed',
  ERROR: 'error',
} as const

export const ANALYSIS_RESULT = {
  CLEAN: 'clean',
  SUSPICIOUS: 'suspicious',
  ERROR: 'error',
} as const

export const MAX_VIDEO_SIZE_MB = 500
export const SUPPORTED_VIDEO_FORMATS = [
  'video/mp4',
  'video/avi',
  'video/mov',
  'video/x-matroska',
]

export const ROUTES = {
  LOGIN: '/login',
  SIGNUP: '/signup',
  HOME: '/',
  VIDEOS: '/videos',
  TICKETS: '/tickets',
  ANALYTICS: '/analytics',
} as const

