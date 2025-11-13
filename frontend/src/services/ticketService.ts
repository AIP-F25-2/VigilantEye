import api from './api'
import type {
  Ticket,
  TicketDetailResponse,
  TicketsListResponse,
  TicketFilters,
} from '@/types/ticket'

export const ticketService = {
  async getTickets(
    page: number = 1,
    perPage: number = 20,
    filters?: TicketFilters
  ): Promise<TicketsListResponse> {
    const params: any = {
      page,
      per_page: perPage,
    }

    if (filters) {
      if (filters.status) params.status = filters.status
      if (filters.priority) params.priority = filters.priority
      if (filters.threat_level) params.threat_level = filters.threat_level
      if (filters.unassigned) {
        // Send 'none' as sentinel value for unassigned tickets
        params.assigned_to = 'none'
      } else if (filters.assigned_to) {
        params.assigned_to = filters.assigned_to
      }
      if (filters.date_from) params.date_from = filters.date_from
      if (filters.date_to) params.date_to = filters.date_to
      if (filters.search) params.search = filters.search
    }

    const response = await api.get<TicketsListResponse>('/tickets', { params })
    return response.data
  },

  async getTicketDetails(ticketId: string): Promise<TicketDetailResponse> {
    const response = await api.get<TicketDetailResponse>(`/tickets/${ticketId}`)
    return response.data
  },

  async acknowledgeTicket(ticketId: string): Promise<Ticket> {
    const response = await api.post<{ ticket: Ticket }>(`/tickets/${ticketId}/acknowledge`)
    return response.data.ticket
  },

  async closeTicket(ticketId: string, reason?: string): Promise<Ticket> {
    const response = await api.post<{ ticket: Ticket }>(`/tickets/${ticketId}/close`, { reason })
    return response.data.ticket
  },

  async escalateTicket(ticketId: string, reason?: string): Promise<Ticket> {
    const response = await api.post<{ ticket: Ticket }>(`/tickets/${ticketId}/escalate`, { reason })
    return response.data.ticket
  },

  async updateStatus(ticketId: string, status: string): Promise<Ticket> {
    const response = await api.patch<{ ticket: Ticket }>(`/tickets/${ticketId}/status`, { status })
    return response.data.ticket
  },

  async assignTicket(ticketId: string, userId: string): Promise<Ticket> {
    const response = await api.patch<{ ticket: Ticket }>(`/tickets/${ticketId}/assign`, {
      user_id: userId,
    })
    return response.data.ticket
  },

  async downloadReport(ticketId: string, format: 'pdf' | 'json' = 'pdf'): Promise<Blob> {
    const response = await api.get(`/tickets/${ticketId}/report/download`, {
      params: { format },
      responseType: 'blob',
    })
    return response.data
  },
}

