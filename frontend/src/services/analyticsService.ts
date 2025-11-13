import api from './api'
import { format, parseISO } from 'date-fns'
import { ticketService } from './ticketService'
import type { TicketAnalytics, DateRange } from '@/types/analytics'
import type { Ticket } from '@/types/ticket'

// Helper function to aggregate tickets into analytics data
async function aggregateFromTickets(dateRange: DateRange | null): Promise<TicketAnalytics> {
  const filters: any = {}
  
  if (dateRange) {
    const from = typeof dateRange.from === 'string' 
      ? dateRange.from 
      : dateRange.from.toISOString()
    const to = typeof dateRange.to === 'string' 
      ? dateRange.to 
      : dateRange.to.toISOString()
    
    filters.date_from = from
    filters.date_to = to
  }

  // Fetch tickets with high limit to get all relevant data
  const { tickets } = await ticketService.getTickets(1, 1000, filters)

  if (tickets.length === 0) {
    return {
      tickets_over_time: [],
      threat_distribution: [],
      response_times: {
        avg_response_time: 0,
        avg_resolution_time: 0,
        p50: 0,
        p95: 0,
        p99: 0,
      },
      top_cameras: [],
      total_tickets: 0,
      open_tickets: 0,
      sla_breach_rate: 0,
    }
  }

  // Group tickets by time period
  const timeGrouped = tickets.reduce((acc, ticket) => {
    const ticketDate = parseISO(ticket.created_at)
    // Use hour grouping for short ranges (< 7 days), day grouping for longer
    const isShortRange = dateRange && 
      (typeof dateRange.from === 'string' 
        ? new Date(dateRange.to).getTime() - new Date(dateRange.from).getTime()
        : dateRange.to.getTime() - dateRange.from.getTime()) < 7 * 24 * 60 * 60 * 1000
    
    const key = isShortRange 
      ? format(ticketDate, 'yyyy-MM-dd HH:00:00')
      : format(ticketDate, 'yyyy-MM-dd 00:00:00')
    
    acc[key] = (acc[key] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const tickets_over_time = Object.entries(timeGrouped)
    .map(([timestamp, count]) => ({
      timestamp: new Date(timestamp).toISOString(),
      count,
    }))
    .sort((a, b) => a.timestamp.localeCompare(b.timestamp))

  // Threat distribution
  const threatCounts = tickets.reduce((acc, ticket) => {
    const level = ticket.threat_level || 'unknown'
    acc[level] = (acc[level] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const totalTickets = tickets.length
  const threat_distribution = Object.entries(threatCounts).map(([threat_level, count]) => ({
    threat_level,
    count,
    percentage: (count / totalTickets) * 100,
  }))

  // Top cameras by incident count
  const cameraCounts = tickets.reduce((acc, ticket) => {
    const cameraId = ticket.video_id || 'unknown'
    if (!acc[cameraId]) {
      acc[cameraId] = { camera_id: cameraId, camera_name: `Camera ${cameraId.substring(0, 8)}`, incident_count: 0 }
    }
    acc[cameraId].incident_count++
    return acc
  }, {} as Record<string, { camera_id: string; camera_name: string; incident_count: number }>)

  const top_cameras = Object.values(cameraCounts)
    .sort((a, b) => b.incident_count - a.incident_count)
    .slice(0, 10)

  // Response times
  const responseTimes = tickets
    .filter(t => t.acknowledged_at)
    .map(t => {
      const created = parseISO(t.created_at)
      const acknowledged = parseISO(t.acknowledged_at!)
      return (acknowledged.getTime() - created.getTime()) / 1000 // seconds
    })

  const resolutionTimes = tickets
    .filter(t => t.closed_at)
    .map(t => {
      const created = parseISO(t.created_at)
      const closed = parseISO(t.closed_at!)
      return (closed.getTime() - created.getTime()) / 1000 // seconds
    })

  const calculatePercentile = (values: number[], percentile: number): number => {
    if (values.length === 0) return 0
    const sorted = [...values].sort((a, b) => a - b)
    const index = Math.ceil((percentile / 100) * sorted.length) - 1
    return sorted[Math.max(0, index)]
  }

  const response_times = {
    avg_response_time: responseTimes.length > 0 
      ? responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length 
      : 0,
    avg_resolution_time: resolutionTimes.length > 0
      ? resolutionTimes.reduce((a, b) => a + b, 0) / resolutionTimes.length
      : 0,
    p50: calculatePercentile(responseTimes, 50),
    p95: calculatePercentile(responseTimes, 95),
    p99: calculatePercentile(responseTimes, 99),
  }

  // SLA breach rate
  const slaBreaches = tickets.filter(t => t.sla_breach).length
  const sla_breach_rate = totalTickets > 0 ? (slaBreaches / totalTickets) * 100 : 0

  // Open tickets
  const open_tickets = tickets.filter(t => t.status !== 'resolved' && t.status !== 'closed').length

  return {
    tickets_over_time,
    threat_distribution,
    response_times,
    top_cameras,
    total_tickets: totalTickets,
    open_tickets,
    sla_breach_rate,
  }
}

export const analyticsService = {
  async getTicketAnalytics(dateRange: DateRange | null): Promise<TicketAnalytics> {
    try {
      const params: any = {}
      
      if (dateRange) {
        const from = typeof dateRange.from === 'string' 
          ? dateRange.from 
          : dateRange.from.toISOString()
        const to = typeof dateRange.to === 'string' 
          ? dateRange.to 
          : dateRange.to.toISOString()
        
        params.from = from
        params.to = to
      }

      const response = await api.get<TicketAnalytics>('/api/analytics/tickets', { params })
      return response.data
    } catch (error: any) {
      // Fallback to client-side aggregation if endpoint is not available (404/501)
      if (error.response?.status === 404 || error.response?.status === 501) {
        return await aggregateFromTickets(dateRange)
      }
      // Re-throw other errors
      throw error
    }
  },
}

