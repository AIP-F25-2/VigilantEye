import type { PaginationInfo } from './video'

export interface Ticket {
  id: string
  video_id: string | null
  title: string
  description: string | null
  priority: 'low' | 'medium' | 'high' | 'critical'
  status: 'open' | 'acknowledged' | 'in_progress' | 'resolved' | 'closed'
  threat_level: 'low' | 'medium' | 'high' | 'critical' | null
  assigned_to: string | null
  assigned_user?: {
    id: string
    username: string
  } | null
  created_by: string
  acknowledged_at: string | null
  closed_at: string | null
  escalated: boolean
  escalation_count: number
  escalation_sent_at: string | null
  sla_breach: boolean
  auto_close_at: string | null
  created_at: string
  updated_at: string
}

export interface Evidence {
  id: string
  video_id: string
  ticket_id: string | null
  type: 'frame' | 'audio' | 'video'
  filepath: string
  timestamp: number | null
  frame_number: number | null
  description: string | null
  ai_analysis: Record<string, any> | null
  is_flagged: boolean
  confidence_score: number | null
  created_at: string
}

export interface Person {
  id: string
  video_id: string
  person_tracking_id: string
  first_seen: string
  last_seen: string
  total_appearances: number
  age_estimate: number | null
  gender: string | null
  ethnicity: string | null
  confidence_score: number
  thumbnail_path: string | null
  clothing_description: string | null
  body_features: Record<string, any> | null
  similar_persons?: Array<{
    person: Person
    similarity: number
  }>
}

export interface TicketHistory {
  id: string
  ticket_id: string
  user_id: string | null
  event: string
  details: Record<string, any> | null
  occurred_at: string
}

export interface TicketDetailResponse {
  ticket: Ticket
  evidence: Evidence[]
  persons_of_interest: Person[]
  history: TicketHistory[]
  video: {
    id: string
    filename: string
    camera: {
      name: string
      location: string | null
    } | null
  } | null
  assigned_user: {
    id: string
    username: string
    email: string
    role: string
  } | null
}

export interface TicketFilters {
  status?: string
  priority?: string
  threat_level?: string
  assigned_to?: string
  unassigned?: boolean
  date_from?: string
  date_to?: string
  search?: string
}

export interface TicketsListResponse {
  tickets: Ticket[]
  pagination: PaginationInfo
}

export type TicketAction = 'acknowledge' | 'close' | 'escalate' | 'assign' | 'update_status'

