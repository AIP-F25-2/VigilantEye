export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api'

// Socket.IO base URL - remove trailing /api segment from API_BASE_URL or use env var
const getSocketBaseUrl = (): string => {
  const envUrl = import.meta.env.VITE_SOCKET_BASE_URL
  if (envUrl) return envUrl
  
  const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api'
  // Remove trailing /api if present
  return apiUrl.replace(/\/api\/?$/, '') || 'http://localhost:5000'
}

export const SOCKET_BASE_URL = getSocketBaseUrl()

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
// Supported video MIME types with mapping comments:
// - video/mp4: MP4 files
// - video/avi: AVI files
// - video/mov, video/quicktime: MOV files (quicktime is the standard MIME type)
// - video/x-matroska: MKV files
export const SUPPORTED_VIDEO_MIME_TYPES = [
  'video/mp4',
  'video/avi',
  'video/mov',
  'video/quicktime',
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

export const PASSWORD_REQUIREMENTS = {
  MIN_LENGTH: 8,
  REQUIRE_UPPERCASE: true,
  REQUIRE_LOWERCASE: true,
  REQUIRE_DIGIT: true,
  REQUIRE_SPECIAL: false, // Optional for now
} as const

export const PASSWORD_REGEX = {
  UPPERCASE: /[A-Z]/,
  LOWERCASE: /[a-z]/,
  DIGIT: /[0-9]/,
  SPECIAL: /[!@#$%^&*(),.?":{}|<>]/,
} as const

// Video Upload Constants
// Derived from SUPPORTED_VIDEO_MIME_TYPES for display purposes
export const SUPPORTED_VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv']

// Stream Constants
export const MAX_CONCURRENT_STREAMS = 4
export const STREAM_URL_PLACEHOLDER = 'rtsp://camera-ip:554/stream'

// Evidence Type Constants
export const EVIDENCE_TYPE = {
  FRAME: 'frame',
  AUDIO: 'audio',
  VIDEO: 'video',
} as const

// Ticket History Event Types
export const TICKET_EVENT = {
  CREATED: 'created',
  ACKNOWLEDGED: 'acknowledged',
  ESCALATED: 'escalated',
  CLOSED: 'closed',
  STATUS_CHANGED: 'status_changed',
  ASSIGNED: 'assigned',
  AUTO_ESCALATED: 'auto_escalated',
  AUTO_CLOSED: 'auto_closed',
} as const

// WebSocket Namespaces
export const WS_NAMESPACE_ANALYSIS = '/analysis'
export const WS_NAMESPACE_TICKETS = '/tickets'
export const WS_NAMESPACE_LOCAL_STREAM = '/local-stream'

