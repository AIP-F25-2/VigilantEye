import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  LogOut,
  Ticket,
  Filter,
  Search,
  Clock,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Eye,
  Plus,
  RefreshCw,
  BarChart3,
  Calendar,
  User,
  Shield,
} from 'lucide-react'
import Logo from '../components/Logo'
import { useAuthStore } from '../store/authStore'
import { ticketAPI } from '../services/api'

const TicketsDashboard = () => {
  const navigate = useNavigate()
  const { user, clearAuth } = useAuthStore()
  
  const [tickets, setTickets] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('')
  const [viewMode, setViewMode] = useState('grid') // 'grid' or 'list'

  const loadTickets = async () => {
    try {
      setLoading(true)
      const params = {}
      if (statusFilter) params.status = statusFilter
      if (priorityFilter) params.priority = priorityFilter
      
      const response = await ticketAPI.getTickets(params)
      setTickets(response.tickets || [])
    } catch (error) {
      console.error('Failed to load tickets:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadStats = async () => {
    try {
      const response = await ticketAPI.getTicketStats()
      setStats(response)
    } catch (error) {
      console.error('Failed to load stats:', error)
    }
  }

  useEffect(() => {
    loadTickets()
    loadStats()
  }, [statusFilter, priorityFilter])

  const handleLogout = () => {
    clearAuth()
    navigate('/login')
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'OPEN':
        return <Clock className="w-4 h-4 text-yellow-500" />
      case 'ACKNOWLEDGED':
        return <CheckCircle className="w-4 h-4 text-blue-500" />
      case 'ESCALATED':
        return <AlertTriangle className="w-4 h-4 text-red-500" />
      case 'CLOSED':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'AUTO_CLOSED':
        return <XCircle className="w-4 h-4 text-gray-500" />
      default:
        return <Ticket className="w-4 h-4 text-gray-500" />
    }
  }

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'CRITICAL':
        return 'text-red-500 bg-red-500/10 border-red-500/30'
      case 'HIGH':
        return 'text-orange-500 bg-orange-500/10 border-orange-500/30'
      case 'MEDIUM':
        return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/30'
      case 'LOW':
        return 'text-green-500 bg-green-500/10 border-green-500/30'
      default:
        return 'text-gray-500 bg-gray-500/10 border-gray-500/30'
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'OPEN':
        return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/30'
      case 'ACKNOWLEDGED':
        return 'text-blue-500 bg-blue-500/10 border-blue-500/30'
      case 'ESCALATED':
        return 'text-red-500 bg-red-500/10 border-red-500/30'
      case 'CLOSED':
        return 'text-green-500 bg-green-500/10 border-green-500/30'
      case 'AUTO_CLOSED':
        return 'text-gray-500 bg-gray-500/10 border-gray-500/30'
      default:
        return 'text-gray-500 bg-gray-500/10 border-gray-500/30'
    }
  }

  const filteredTickets = tickets.filter(ticket => {
    const matchesSearch = ticket.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         ticket.ticket_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         ticket.description.toLowerCase().includes(searchTerm.toLowerCase())
    return matchesSearch
  })

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatTimeAgo = (dateString) => {
    const now = new Date()
    const date = new Date(dateString)
    const diffMs = now - date
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMins / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    return `${diffDays}d ago`
  }

  return (
    <div className="min-h-screen bg-dark-950 grid-bg">
      {/* Header */}
      <header className="border-b border-gray-800 bg-dark-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <Logo size="md" />
            
            <div className="flex items-center gap-6">
              {/* User Info */}
              <div className="flex items-center gap-3 px-4 py-2 bg-dark-800 rounded-lg border border-gray-700">
                <div className="w-8 h-8 bg-primary-500/20 rounded-full flex items-center justify-center">
                  {user?.role === 'ADMIN' ? (
                    <Shield className="w-4 h-4 text-primary-500" />
                  ) : (
                    <User className="w-4 h-4 text-primary-500" />
                  )}
                </div>
                <div className="text-sm">
                  <div className="font-medium text-gray-200">{user?.username}</div>
                  <div className="text-xs text-gray-500">{user?.role}</div>
                </div>
              </div>

              {/* Navigation */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => navigate('/dashboard')}
                  className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
                >
                  Dashboard
                </button>
                <button
                  onClick={() => navigate('/tickets')}
                  className="px-4 py-2 bg-primary-600 text-white rounded-lg"
                >
                  Tickets
                </button>
              </div>

              {/* Logout Button */}
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg transition-colors border border-red-500/30"
              >
                <LogOut className="w-4 h-4" />
                <span className="text-sm font-medium">Logout</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Header Section */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-2 flex items-center gap-3">
              <Ticket className="w-8 h-8 text-primary-500" />
              Ticket Management
            </h1>
            <p className="text-gray-400">
              Monitor and manage security threat tickets
            </p>
          </div>
          
          <div className="flex items-center gap-4">
            <button
              onClick={() => {
                loadTickets()
                loadStats()
              }}
              className="flex items-center gap-2 px-4 py-2 bg-dark-800 hover:bg-dark-700 text-gray-300 rounded-lg transition-colors border border-gray-700"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
            
            <div className="flex items-center gap-2">
              <button
                onClick={() => setViewMode('grid')}
                className={`p-2 rounded-lg transition-colors ${
                  viewMode === 'grid' 
                    ? 'bg-primary-600 text-white' 
                    : 'bg-dark-800 text-gray-400 hover:bg-dark-700'
                }`}
              >
                <BarChart3 className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-2 rounded-lg transition-colors ${
                  viewMode === 'list' 
                    ? 'bg-primary-600 text-white' 
                    : 'bg-dark-800 text-gray-400 hover:bg-dark-700'
                }`}
              >
                <Calendar className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className="card">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 bg-yellow-500/20 rounded-lg flex items-center justify-center">
                  <Clock className="w-5 h-5 text-yellow-500" />
                </div>
                <h3 className="font-semibold">Open</h3>
              </div>
              <div className="text-2xl font-bold text-yellow-500">{stats.open_tickets}</div>
            </div>

            <div className="card">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center">
                  <CheckCircle className="w-5 h-5 text-blue-500" />
                </div>
                <h3 className="font-semibold">Acknowledged</h3>
              </div>
              <div className="text-2xl font-bold text-blue-500">{stats.acknowledged_tickets}</div>
            </div>

            <div className="card">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 bg-red-500/20 rounded-lg flex items-center justify-center">
                  <AlertTriangle className="w-5 h-5 text-red-500" />
                </div>
                <h3 className="font-semibold">Escalated</h3>
              </div>
              <div className="text-2xl font-bold text-red-500">{stats.escalated_tickets}</div>
            </div>

            <div className="card">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 bg-green-500/20 rounded-lg flex items-center justify-center">
                  <CheckCircle className="w-5 h-5 text-green-500" />
                </div>
                <h3 className="font-semibold">Closed</h3>
              </div>
              <div className="text-2xl font-bold text-green-500">{stats.closed_tickets}</div>
            </div>
          </div>
        )}

        {/* Filters and Search */}
        <div className="card-glass mb-6">
          <div className="flex flex-col lg:flex-row gap-4">
            {/* Search */}
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search tickets..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-dark-800 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:border-primary-500 focus:outline-none"
                />
              </div>
            </div>

            {/* Filters */}
            <div className="flex gap-4">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-4 py-2 bg-dark-800 border border-gray-700 rounded-lg text-white focus:border-primary-500 focus:outline-none"
              >
                <option value="">All Status</option>
                <option value="OPEN">Open</option>
                <option value="ACKNOWLEDGED">Acknowledged</option>
                <option value="ESCALATED">Escalated</option>
                <option value="CLOSED">Closed</option>
                <option value="AUTO_CLOSED">Auto Closed</option>
              </select>

              <select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
                className="px-4 py-2 bg-dark-800 border border-gray-700 rounded-lg text-white focus:border-primary-500 focus:outline-none"
              >
                <option value="">All Priority</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
            </div>
          </div>
        </div>

        {/* Tickets List */}
        <div className="card-glass">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="w-8 h-8 text-primary-500 animate-spin" />
              <span className="ml-3 text-gray-400">Loading tickets...</span>
            </div>
          ) : filteredTickets.length === 0 ? (
            <div className="text-center py-12">
              <Ticket className="w-16 h-16 mx-auto mb-4 text-gray-600" />
              <h3 className="text-lg font-medium text-gray-300 mb-2">No tickets found</h3>
              <p className="text-gray-500">
                {searchTerm || statusFilter || priorityFilter 
                  ? 'Try adjusting your filters' 
                  : 'No tickets have been created yet'
                }
              </p>
            </div>
          ) : viewMode === 'grid' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredTickets.map((ticket) => (
                <div
                  key={ticket.id}
                  onClick={() => navigate(`/tickets/${ticket.id}`)}
                  className="bg-dark-800 rounded-lg p-6 border border-gray-700 hover:border-primary-500/50 transition-colors cursor-pointer group"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(ticket.status)}
                      <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(ticket.status)}`}>
                        {ticket.status}
                      </span>
                    </div>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getPriorityColor(ticket.priority)}`}>
                      {ticket.priority}
                    </span>
                  </div>

                  <h3 className="font-semibold text-gray-200 mb-2 group-hover:text-primary-400 transition-colors">
                    {ticket.title}
                  </h3>
                  
                  <p className="text-sm text-gray-400 mb-4 line-clamp-2">
                    {ticket.description}
                  </p>

                  <div className="flex items-center justify-between text-xs text-gray-500">
                    <span>{ticket.ticket_number}</span>
                    <span>{formatTimeAgo(ticket.created_at)}</span>
                  </div>

                  {ticket.total_evidence_files > 0 && (
                    <div className="mt-3 flex items-center gap-2 text-xs text-primary-400">
                      <Eye className="w-3 h-3" />
                      <span>{ticket.total_evidence_files} evidence files</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-4">
              {filteredTickets.map((ticket) => (
                <div
                  key={ticket.id}
                  onClick={() => navigate(`/tickets/${ticket.id}`)}
                  className="bg-dark-800 rounded-lg p-6 border border-gray-700 hover:border-primary-500/50 transition-colors cursor-pointer group"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      {getStatusIcon(ticket.status)}
                      <div>
                        <h3 className="font-semibold text-gray-200 group-hover:text-primary-400 transition-colors">
                          {ticket.title}
                        </h3>
                        <p className="text-sm text-gray-400">{ticket.ticket_number}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(ticket.status)}`}>
                        {ticket.status}
                      </span>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getPriorityColor(ticket.priority)}`}>
                        {ticket.priority}
                      </span>
                      <span className="text-xs text-gray-500">{formatTimeAgo(ticket.created_at)}</span>
                      <Eye className="w-4 h-4 text-gray-400 group-hover:text-primary-400 transition-colors" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

export default TicketsDashboard
