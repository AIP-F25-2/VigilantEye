import { useState, useEffect, useCallback, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Eye,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Download,
  RefreshCw,
  FileText,
  ChevronLeft,
  ChevronRight,
  Search,
  X,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '@/hooks/useAuth'
import { useWebSocket } from '@/hooks/useWebSocket'
import { useDebounce } from '@/hooks/useDebounce'
import { ticketService } from '@/services/ticketService'
import { authService } from '@/services/authService'
import type { User as UserType } from '@/types/auth'
import { Button } from '@/components/Button'
import { TicketStatusBadge } from '@/components/TicketStatusBadge'
import { PriorityBadge } from '@/components/PriorityBadge'
import { ThreatLevelBadge } from '@/components/ThreatLevelBadge'
import { TTLCountdown } from '@/components/TTLCountdown'
import { TicketDetailModal } from '@/components/TicketDetailModal'
import { CloseTicketDialog } from '@/components/CloseTicketDialog'
import { formatRelativeTime } from '@/utils/formatters'
import { WS_NAMESPACE_TICKETS } from '@/utils/constants'
import type { Ticket, TicketFilters } from '@/types/ticket'
import type { AxiosError } from 'axios'

export default function TicketsPage() {
  const { user, isAdmin } = useAuth()
  const { socket, isConnected } = useWebSocket(WS_NAMESPACE_TICKETS)
  const queryClient = useQueryClient()

  // State
  const [page, setPage] = useState(1)
  const perPage = 20
  const [filters, setFilters] = useState<TicketFilters>({})
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null)
  const [ticketToClose, setTicketToClose] = useState<Ticket | null>(null)

  // Filter state
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [priority, setPriority] = useState('')
  const [threatLevel, setThreatLevel] = useState('')
  const [assignedTo, setAssignedTo] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [users, setUsers] = useState<UserType[]>([])

  // Fetch users for admin filter
  useEffect(() => {
    if (isAdmin) {
      authService
        .getUsers()
        .then(setUsers)
        .catch((err) => {
          console.error('Failed to fetch users:', err)
        })
    }
  }, [isAdmin])

  // Debounce search
  const debouncedSearch = useDebounce(search, 500)

  // Compute stable query key
  const filtersKey = useMemo(() => {
    return JSON.stringify({
      status: filters.status || '',
      priority: filters.priority || '',
      threat_level: filters.threat_level || '',
      assigned_to: filters.assigned_to || '',
      date_from: filters.date_from || '',
      date_to: filters.date_to || '',
      search: filters.search || '',
    })
  }, [filters])

  // Sync filter state with filters prop
  useEffect(() => {
    setSearch(filters.search || '')
    setStatus(filters.status || '')
    setPriority(filters.priority || '')
    setThreatLevel(filters.threat_level || '')
    setAssignedTo(filters.assigned_to || '')
    setDateFrom(filters.date_from || '')
    setDateTo(filters.date_to || '')
  }, [filters])

  // Update filters when filter values change
  useEffect(() => {
    const filters: TicketFilters = {
      search: debouncedSearch || undefined,
      status: status || undefined,
      priority: priority || undefined,
      threat_level: threatLevel || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    }
    
    // Handle assigned_to filter
    if (assignedTo === 'unassigned') {
      filters.unassigned = true
    } else if (assignedTo && assignedTo !== 'unassigned') {
      filters.assigned_to = assignedTo
    }
    
    setFilters(filters)
    setPage(1) // Reset to page 1 when filters change
  }, [debouncedSearch, status, priority, threatLevel, assignedTo, dateFrom, dateTo])

  // React Query: Fetch Tickets
  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['tickets', page, filtersKey],
    queryFn: () => ticketService.getTickets(page, perPage, filters),
    keepPreviousData: true,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  const tickets = data?.tickets || []
  const pagination = data?.pagination

  // React Query: Acknowledge Mutation
  const acknowledgeMutation = useMutation({
    mutationFn: (ticketId: string) => ticketService.acknowledgeTicket(ticketId),
    onMutate: async (ticketId) => {
      // Optimistic update
      await queryClient.cancelQueries({ queryKey: ['tickets', page, filtersKey] })
      const previousData = queryClient.getQueryData(['tickets', page, filtersKey])
      queryClient.setQueryData(['tickets', page, filtersKey], (old: any) => {
        if (!old) return old
        return {
          ...old,
          tickets: old.tickets.map((t: Ticket) =>
            t.id === ticketId
              ? {
                  ...t,
                  status: 'acknowledged' as const,
                  assigned_to: user?.id || null,
                  assigned_user: user
                    ? {
                        id: user.id,
                        username: user.username,
                      }
                    : null,
                }
              : t
          ),
        }
      })
      return { previousData }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] })
      toast.success('Ticket acknowledged successfully')
      setSelectedTicket(null)
    },
    onError: (err: any, ticketId, context) => {
      if (context?.previousData) {
        queryClient.setQueryData(['tickets', page, filtersKey], context.previousData)
      }
      const errorMessage = err.response?.data?.error || err.message || 'Failed to acknowledge ticket'
      toast.error(errorMessage)
    },
  })

  // React Query: Close Mutation
  const closeMutation = useMutation({
    mutationFn: ({ ticketId, reason }: { ticketId: string; reason?: string }) =>
      ticketService.closeTicket(ticketId, reason),
    onMutate: async (variables) => {
      await queryClient.cancelQueries({ queryKey: ['tickets', page, filtersKey] })
      const previousData = queryClient.getQueryData(['tickets', page, filtersKey])
      queryClient.setQueryData(['tickets', page, filtersKey], (old: any) => {
        if (!old) return old
        return {
          ...old,
          tickets: old.tickets.map((t: Ticket) =>
            t.id === variables.ticketId ? { ...t, status: 'closed' as const } : t
          ),
        }
      })
      return { previousData }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] })
      toast.success('Ticket closed successfully')
      setTicketToClose(null)
    },
    onError: (err: any, variables, context) => {
      if (context?.previousData) {
        queryClient.setQueryData(['tickets', page, filtersKey], context.previousData)
      }
      const errorMessage = err.response?.data?.error || err.message || 'Failed to close ticket'
      toast.error(errorMessage)
    },
  })

  // React Query: Escalate Mutation
  const escalateMutation = useMutation({
    mutationFn: ({ ticketId, reason }: { ticketId: string; reason?: string }) =>
      ticketService.escalateTicket(ticketId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] })
      toast.success('Escalation alert sent to Telegram')
    },
    onError: (err: any) => {
      const errorMessage = err.response?.data?.error || err.message || 'Failed to escalate ticket'
      toast.error(errorMessage)
    },
  })

  // WebSocket: Real-Time Updates
  useEffect(() => {
    if (!socket) return

    const handleTicketUpdate = (data: {
      ticket_id: string
      status?: string
      escalated?: boolean
      assigned_to?: string | null
      assigned_user?: { id: string; username: string } | null
      [key: string]: any
    }) => {
      queryClient.setQueryData(['tickets', page, filtersKey], (old: any) => {
        if (!old) return old
        return {
          ...old,
          tickets: old.tickets.map((t: Ticket) =>
            t.id === data.ticket_id
              ? {
                  ...t,
                  ...(data.status && { status: data.status as Ticket['status'] }),
                  ...(data.escalated !== undefined && { escalated: data.escalated }),
                  ...(data.assigned_to !== undefined && { assigned_to: data.assigned_to }),
                  ...(data.assigned_user !== undefined && { assigned_user: data.assigned_user }),
                }
              : t
          ),
        }
      })
      toast.info(`Ticket ${data.ticket_id.substring(0, 8)} updated`)
    }

    socket.on('ticket_status_changed', handleTicketUpdate)
    socket.on('ticket_acknowledged', handleTicketUpdate)
    socket.on('ticket_closed', handleTicketUpdate)
    socket.on('ticket_escalated', handleTicketUpdate)

    return () => {
      socket.off('ticket_status_changed', handleTicketUpdate)
      socket.off('ticket_acknowledged', handleTicketUpdate)
      socket.off('ticket_closed', handleTicketUpdate)
      socket.off('ticket_escalated', handleTicketUpdate)
    }
  }, [socket, queryClient, page, filtersKey])

  // Action Handlers
  const handleViewDetails = useCallback((ticket: Ticket) => {
    setSelectedTicket(ticket)
  }, [])

  const handleAcknowledge = useCallback(
    (ticketId: string) => {
      acknowledgeMutation.mutate(ticketId)
    },
    [acknowledgeMutation]
  )

  const handleClose = useCallback((ticket: Ticket) => {
    setTicketToClose(ticket)
  }, [])

  const handleCloseConfirm = useCallback(
    (reason?: string) => {
      if (ticketToClose) {
        closeMutation.mutate({ ticketId: ticketToClose.id, reason })
      }
    },
    [ticketToClose, closeMutation]
  )

  const handleEscalate = useCallback(
    (ticketId: string) => {
      escalateMutation.mutate({ ticketId })
    },
    [escalateMutation]
  )

  const handleDownloadReport = useCallback(async (ticketId: string) => {
    try {
      const blob = await ticketService.downloadReport(ticketId, 'pdf')
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `VigilentEye_Report_${ticketId.substring(0, 8)}.pdf`
      a.click()
      URL.revokeObjectURL(url)
      toast.success('Report downloaded successfully')
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || err.message || 'Failed to download report'
      toast.error(errorMessage)
    }
  }, [])

  // Filter Handlers
  const handleResetFilters = useCallback(() => {
    setSearch('')
    setStatus('')
    setPriority('')
    setThreatLevel('')
    setAssignedTo('')
    setDateFrom('')
    setDateTo('')
    setFilters({})
    setPage(1)
  }, [])

  // Pagination Handlers
  const handlePageChange = useCallback((newPage: number) => {
    setPage(newPage)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])

  // Pagination Component
  const renderPagination = () => {
    if (!pagination || pagination.pages <= 1) return null

    const { page: currentPage, pages, total } = pagination
    const start = (currentPage - 1) * perPage + 1
    const end = Math.min(currentPage * perPage, total)

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
          <span className="font-medium">{total}</span> tickets
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

  const hasActiveFilters = search || status || priority || threatLevel || assignedTo || dateFrom || dateTo

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <FileText className="h-8 w-8" />
            Security Tickets
          </h1>
          <p className="mt-2 text-gray-600">Manage and investigate security incidents</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div
              className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}
              title={isConnected ? 'WebSocket Connected' : 'WebSocket Disconnected'}
            />
            <span className="text-sm text-gray-600">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          <Button onClick={() => refetch()} variant="secondary" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white rounded-lg shadow-md p-4 mb-6">
        <div className="flex flex-wrap gap-4 items-end">
          {/* Search Input */}
          <div className="flex-1 min-w-[200px]">
            <label htmlFor="search" className="block text-sm font-medium text-gray-700 mb-1">
              Search
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                id="search"
                type="text"
                placeholder="Search by title..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10 pr-3 py-2 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm border"
              />
            </div>
          </div>

          {/* Status Dropdown */}
          <div className="min-w-[150px]">
            <label htmlFor="status" className="block text-sm font-medium text-gray-700 mb-1">
              Status
            </label>
            <select
              id="status"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm px-3 py-2 border"
            >
              <option value="">All</option>
              <option value="open">Open</option>
              <option value="acknowledged">Acknowledged</option>
              <option value="in_progress">In Progress</option>
              <option value="resolved">Resolved</option>
              <option value="closed">Closed</option>
            </select>
          </div>

          {/* Priority Dropdown */}
          <div className="min-w-[150px]">
            <label htmlFor="priority" className="block text-sm font-medium text-gray-700 mb-1">
              Priority
            </label>
            <select
              id="priority"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm px-3 py-2 border"
            >
              <option value="">All</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>

          {/* Threat Level Dropdown */}
          <div className="min-w-[150px]">
            <label htmlFor="threat-level" className="block text-sm font-medium text-gray-700 mb-1">
              Threat Level
            </label>
            <select
              id="threat-level"
              value={threatLevel}
              onChange={(e) => setThreatLevel(e.target.value)}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm px-3 py-2 border"
            >
              <option value="">All</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>

          {/* Assigned To Dropdown */}
          <div className="min-w-[150px]">
            <label htmlFor="assigned-to" className="block text-sm font-medium text-gray-700 mb-1">
              Assigned To
            </label>
            <select
              id="assigned-to"
              value={assignedTo}
              onChange={(e) => setAssignedTo(e.target.value)}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm px-3 py-2 border"
            >
              <option value="">All</option>
              <option value="unassigned">Unassigned</option>
              {user && <option value={user.id}>Me</option>}
              {isAdmin &&
                users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.username}
                  </option>
                ))}
            </select>
          </div>

          {/* Date Range */}
          <div className="flex gap-2">
            <div className="min-w-[140px]">
              <label htmlFor="date-from" className="block text-sm font-medium text-gray-700 mb-1">
                From
              </label>
              <input
                id="date-from"
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm px-3 py-2 border"
              />
            </div>
            <div className="min-w-[140px]">
              <label htmlFor="date-to" className="block text-sm font-medium text-gray-700 mb-1">
                To
              </label>
              <input
                id="date-to"
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm px-3 py-2 border"
              />
            </div>
          </div>

          {/* Reset Button */}
          {hasActiveFilters && (
            <div>
              <Button onClick={handleResetFilters} variant="ghost" size="md">
                <X className="mr-2 h-4 w-4" />
                Reset
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Table */}
      {isLoading && (
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          <div className="animate-pulse space-y-4 p-6">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-16 bg-gray-200 rounded" />
            ))}
          </div>
        </div>
      )}

      {isError && (
        <div className="bg-white rounded-lg shadow-md p-6 text-center">
          <p className="text-red-600 mb-4">
            {(error as AxiosError)?.response?.data
              ? ((error as AxiosError).response?.data as any)?.error
              : 'Failed to load tickets'}
          </p>
          <Button onClick={() => refetch()} variant="primary">
            Retry
          </Button>
        </div>
      )}

      {!isLoading && !isError && tickets.length === 0 && (
        <div className="bg-white rounded-lg shadow-md p-12 text-center">
          <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 mb-4">
            {hasActiveFilters ? 'No tickets match your filters' : 'No security incidents detected'}
          </p>
          {hasActiveFilters ? (
            <Button onClick={handleResetFilters} variant="primary">
              Reset Filters
            </Button>
          ) : (
            <p className="text-sm text-gray-500">All clear! No suspicious activity has been detected.</p>
          )}
        </div>
      )}

      {!isLoading && !isError && tickets.length > 0 && (
        <>
          <div className="bg-white rounded-lg shadow-md overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Ticket ID
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Title
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Priority
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider hidden md:table-cell">
                      Threat Level
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Created
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider hidden md:table-cell">
                      Assigned To
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {tickets.map((ticket) => (
                    <tr
                      key={ticket.id}
                      className="hover:bg-gray-50 transition-colors cursor-pointer"
                      onClick={() => handleViewDetails(ticket)}
                    >
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-sm font-mono text-gray-900">
                          {ticket.id.substring(0, 8)}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm font-medium text-gray-900">
                          {ticket.title.length > 50
                            ? `${ticket.title.substring(0, 50)}...`
                            : ticket.title}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <TicketStatusBadge status={ticket.status} />
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <PriorityBadge priority={ticket.priority} />
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap hidden md:table-cell">
                        <ThreatLevelBadge threatLevel={ticket.threat_level} />
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatRelativeTime(ticket.created_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 hidden md:table-cell">
                        {ticket.assigned_user?.username || (ticket.assigned_to === user?.id ? 'Me' : 'Unassigned')}
                      </td>
                      <td
                        className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            onClick={() => handleViewDetails(ticket)}
                            variant="ghost"
                            size="sm"
                            title="View details"
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          {ticket.status === 'open' && (
                            <Button
                              onClick={() => handleAcknowledge(ticket.id)}
                              variant="ghost"
                              size="sm"
                              disabled={acknowledgeMutation.isLoading}
                              title="Acknowledge"
                            >
                              <CheckCircle className="h-4 w-4 text-green-600" />
                            </Button>
                          )}
                          {ticket.status !== 'closed' && (
                            <Button
                              onClick={() => handleClose(ticket)}
                              variant="ghost"
                              size="sm"
                              title="Close"
                            >
                              <XCircle className="h-4 w-4 text-red-600" />
                            </Button>
                          )}
                          {!ticket.escalated && (
                            <Button
                              onClick={() => handleEscalate(ticket.id)}
                              variant="ghost"
                              size="sm"
                              disabled={escalateMutation.isLoading}
                              title="Escalate"
                            >
                              <AlertTriangle className="h-4 w-4 text-orange-600" />
                            </Button>
                          )}
                          <Button
                            onClick={() => handleDownloadReport(ticket.id)}
                            variant="ghost"
                            size="sm"
                            title="Download report"
                          >
                            <Download className="h-4 w-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {renderPagination()}
        </>
      )}

      {/* Modals */}
      <TicketDetailModal
        ticket={selectedTicket}
        onClose={() => setSelectedTicket(null)}
        onAcknowledge={handleAcknowledge}
        onCloseTicket={handleClose}
        onEscalate={handleEscalate}
        onDownloadReport={handleDownloadReport}
      />

      <CloseTicketDialog
        ticket={ticketToClose}
        onConfirm={handleCloseConfirm}
        onCancel={() => setTicketToClose(null)}
        isClosing={closeMutation.isLoading}
      />
    </div>
  )
}

