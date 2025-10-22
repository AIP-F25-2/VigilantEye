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
  ChevronDown,
  ChevronRight,
  Image,
  Video,
  Music,
  Download,
  Trash2,
  Play,
  Pause,
  Volume2,
  VolumeX,
  X,
  FileText,
  Archive,
  MoreVertical,
} from 'lucide-react'
import Logo from '../components/Logo'
import { useAuthStore } from '../store/authStore'
import { ticketAPI } from '../services/api'

const UnifiedTicketsPage = () => {
  const navigate = useNavigate()
  const { user, clearAuth } = useAuthStore()
  
  const [tickets, setTickets] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('')
  const [expandedTickets, setExpandedTickets] = useState(new Set())
  const [selectedMedia, setSelectedMedia] = useState(null)
  const [actionLoading, setActionLoading] = useState({})
  const [audioPlaying, setAudioPlaying] = useState(null)

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

  const toggleExpanded = (ticketId) => {
    const newExpanded = new Set(expandedTickets)
    if (newExpanded.has(ticketId)) {
      newExpanded.delete(ticketId)
    } else {
      newExpanded.add(ticketId)
    }
    setExpandedTickets(newExpanded)
  }

  const handleAcknowledge = async (ticketId) => {
    try {
      setActionLoading(prev => ({ ...prev, [ticketId]: true }))
      await ticketAPI.acknowledgeTicket(ticketId)
      await loadTickets()
    } catch (error) {
      console.error('Failed to acknowledge ticket:', error)
    } finally {
      setActionLoading(prev => ({ ...prev, [ticketId]: false }))
    }
  }

  const handleClose = async (ticketId) => {
    try {
      setActionLoading(prev => ({ ...prev, [ticketId]: true }))
      await ticketAPI.closeTicket(ticketId)
      await loadTickets()
    } catch (error) {
      console.error('Failed to close ticket:', error)
    } finally {
      setActionLoading(prev => ({ ...prev, [ticketId]: false }))
    }
  }

  const handleDeleteTicket = async (ticketId) => {
    if (!confirm('Are you sure you want to delete this ticket? This action cannot be undone.')) return
    
    try {
      setActionLoading(prev => ({ ...prev, [ticketId]: true }))
      await ticketAPI.deleteTicket(ticketId)
      await loadTickets()
    } catch (error) {
      console.error('Failed to delete ticket:', error)
    } finally {
      setActionLoading(prev => ({ ...prev, [ticketId]: false }))
    }
  }

  const handleDeleteMedia = async (ticketId, evidenceId) => {
    if (!confirm('Are you sure you want to delete this media file?')) return
    
    try {
      await ticketAPI.deleteEvidence(ticketId, evidenceId)
      await loadTickets()
    } catch (error) {
      console.error('Failed to delete media:', error)
    }
  }

  const handleDownloadMedia = (mediaPath, fileName) => {
    // Create download link
    const link = document.createElement('a')
    link.href = mediaPath
    link.download = fileName
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const handleDownloadAll = async (ticketId) => {
    try {
      const response = await ticketAPI.downloadAllEvidence(ticketId)
      // Handle zip download
      const blob = new Blob([response], { type: 'application/zip' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `ticket_${ticketId}_evidence.zip`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Failed to download all evidence:', error)
    }
  }

  const toggleAudio = (mediaPath) => {
    if (audioPlaying === mediaPath) {
      setAudioPlaying(null)
    } else {
      setAudioPlaying(mediaPath)
    }
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

  const getMediaIcon = (fileName) => {
    const extension = fileName.split('.').pop().toLowerCase()
    if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(extension)) {
      return <Image className="w-4 h-4 text-blue-500" />
    } else if (['mp4', 'avi', 'mov', 'webm'].includes(extension)) {
      return <Video className="w-4 h-4 text-purple-500" />
    } else if (['mp3', 'wav', 'ogg'].includes(extension)) {
      return <Music className="w-4 h-4 text-green-500" />
    } else if (['pdf', 'txt', 'doc', 'docx'].includes(extension)) {
      return <FileText className="w-4 h-4 text-orange-500" />
    } else if (['zip', 'rar', '7z'].includes(extension)) {
      return <Archive className="w-4 h-4 text-gray-500" />
    } else {
      return <FileText className="w-4 h-4 text-gray-500" />
    }
  }

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

  const filteredTickets = tickets.filter(ticket => {
    const matchesSearch = ticket.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         ticket.ticket_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         ticket.description.toLowerCase().includes(searchTerm.toLowerCase())
    return matchesSearch
  })

  const canAcknowledge = (ticket) => ticket.status === 'OPEN' || ticket.status === 'ESCALATED'
  const canClose = (ticket) => ticket.status !== 'CLOSED' && ticket.status !== 'AUTO_CLOSED'
  const isAdmin = user?.role === 'ADMIN'

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
              Monitor and manage security threat tickets with integrated media
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

        {/* Tickets Table */}
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
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-700">
                    <th className="text-left py-4 px-6 text-gray-400 font-medium">Ticket</th>
                    <th className="text-left py-4 px-6 text-gray-400 font-medium">Status</th>
                    <th className="text-left py-4 px-6 text-gray-400 font-medium">Priority</th>
                    <th className="text-left py-4 px-6 text-gray-400 font-medium">Created</th>
                    <th className="text-left py-4 px-6 text-gray-400 font-medium">Media</th>
                    <th className="text-left py-4 px-6 text-gray-400 font-medium">Actions</th>
                    <th className="text-left py-4 px-6 text-gray-400 font-medium w-12"></th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTickets.map((ticket) => (
                    <>
                      {/* Main Row */}
                      <tr 
                        key={ticket.id}
                        className="border-b border-gray-800 hover:bg-dark-800/50 transition-colors cursor-pointer"
                        onClick={() => toggleExpanded(ticket.id)}
                      >
                        <td className="py-4 px-6">
                          <div>
                            <div className="font-medium text-gray-200 mb-1">{ticket.title}</div>
                            <div className="text-sm text-gray-500">{ticket.ticket_number}</div>
                          </div>
                        </td>
                        <td className="py-4 px-6">
                          <div className="flex items-center gap-2">
                            {getStatusIcon(ticket.status)}
                            <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(ticket.status)}`}>
                              {ticket.status}
                            </span>
                          </div>
                        </td>
                        <td className="py-4 px-6">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getPriorityColor(ticket.priority)}`}>
                            {ticket.priority}
                          </span>
                        </td>
                        <td className="py-4 px-6">
                          <div className="text-sm text-gray-400">
                            {formatDate(ticket.created_at)}
                          </div>
                          <div className="text-xs text-gray-500">
                            {formatTimeAgo(ticket.created_at)}
                          </div>
                        </td>
                        <td className="py-4 px-6">
                          <div className="flex items-center gap-2 text-sm text-gray-400">
                            <Image className="w-4 h-4" />
                            <span>{ticket.total_evidence_files} files</span>
                          </div>
                        </td>
                        <td className="py-4 px-6">
                          <div className="flex items-center gap-2">
                            {canAcknowledge(ticket) && (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  handleAcknowledge(ticket.id)
                                }}
                                disabled={actionLoading[ticket.id]}
                                className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded transition-colors disabled:opacity-50"
                              >
                                Ack
                              </button>
                            )}
                            
                            {canClose(ticket) && (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  handleClose(ticket.id)
                                }}
                                disabled={actionLoading[ticket.id]}
                                className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-xs rounded transition-colors disabled:opacity-50"
                              >
                                Close
                              </button>
                            )}
                          </div>
                        </td>
                        <td className="py-4 px-6">
                          {expandedTickets.has(ticket.id) ? (
                            <ChevronDown className="w-4 h-4 text-gray-400" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-gray-400" />
                          )}
                        </td>
                      </tr>

                      {/* Expanded Row */}
                      {expandedTickets.has(ticket.id) && (
                        <tr className="border-b border-gray-800">
                          <td colSpan="7" className="p-0">
                            <div className="bg-dark-800/50 p-6">
                              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                {/* Ticket Details */}
                                <div>
                                  <h3 className="font-semibold text-gray-200 mb-4">Ticket Details</h3>
                                  <div className="space-y-3 text-sm">
                                    <div>
                                      <span className="text-gray-400">Description:</span>
                                      <p className="text-gray-300 mt-1">{ticket.description}</p>
                                    </div>
                                    <div>
                                      <span className="text-gray-400">Video ID:</span>
                                      <span className="text-gray-300 ml-2">{ticket.video_id}</span>
                                    </div>
                                    <div>
                                      <span className="text-gray-400">Timestamp:</span>
                                      <span className="text-gray-300 ml-2">{(ticket.frame_timestamp_ms / 1000).toFixed(2)}s</span>
                                    </div>
                                    {ticket.notes && (
                                      <div>
                                        <span className="text-gray-400">Notes:</span>
                                        <p className="text-gray-300 mt-1 whitespace-pre-wrap">{ticket.notes}</p>
                                      </div>
                                    )}
                                  </div>
                                </div>

                                {/* Media Gallery */}
                                <div>
                                  <div className="flex items-center justify-between mb-4">
                                    <h3 className="font-semibold text-gray-200">Evidence Media</h3>
                                    <div className="flex items-center gap-2">
                                      <button
                                        onClick={() => handleDownloadAll(ticket.id)}
                                        className="flex items-center gap-1 px-3 py-1 bg-primary-600 hover:bg-primary-700 text-white text-xs rounded transition-colors"
                                      >
                                        <Download className="w-3 h-3" />
                                        Download All
                                      </button>
                                      {isAdmin && (
                                        <button
                                          onClick={() => handleDeleteTicket(ticket.id)}
                                          className="flex items-center gap-1 px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-xs rounded transition-colors"
                                        >
                                          <Trash2 className="w-3 h-3" />
                                          Delete Ticket
                                        </button>
                                      )}
                                    </div>
                                  </div>

                                  {/* Media Grid */}
                                  <div className="grid grid-cols-2 gap-3">
                                    {ticket.evidence_files?.map((media) => (
                                      <div
                                        key={media.id}
                                        className="bg-dark-700 rounded-lg p-3 border border-gray-600 hover:border-primary-500/50 transition-colors group"
                                      >
                                        <div className="flex items-center gap-2 mb-2">
                                          {getMediaIcon(media.file_name)}
                                          <span className="text-xs text-gray-300 truncate flex-1">
                                            {media.file_name}
                                          </span>
                                          {isAdmin && (
                                            <button
                                              onClick={() => handleDeleteMedia(ticket.id, media.id)}
                                              className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 transition-opacity"
                                            >
                                              <Trash2 className="w-3 h-3" />
                                            </button>
                                          )}
                                        </div>
                                        
                                        <div className="flex items-center gap-1">
                                          <button
                                            onClick={() => setSelectedMedia(media)}
                                            className="flex-1 flex items-center justify-center gap-1 px-2 py-1 bg-dark-600 hover:bg-dark-500 text-gray-300 text-xs rounded transition-colors"
                                          >
                                            <Eye className="w-3 h-3" />
                                            View
                                          </button>
                                          <button
                                            onClick={() => handleDownloadMedia(media.file_path, media.file_name)}
                                            className="flex items-center justify-center px-2 py-1 bg-dark-600 hover:bg-dark-500 text-gray-300 text-xs rounded transition-colors"
                                          >
                                            <Download className="w-3 h-3" />
                                          </button>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>

      {/* Media Viewer Modal */}
      {selectedMedia && (
        <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-50 p-4"
             onClick={() => setSelectedMedia(null)}>
          <div className="max-w-4xl max-h-full bg-dark-800 rounded-lg overflow-hidden border border-gray-700"
               onClick={(e) => e.stopPropagation()}>
            <div className="p-4 border-b border-gray-700 flex items-center justify-between">
              <h3 className="font-semibold text-gray-200">{selectedMedia.file_name}</h3>
              <button
                onClick={() => setSelectedMedia(null)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-4">
              {selectedMedia.file_name.match(/\.(jpg|jpeg|png|gif|webp)$/i) ? (
                <div className="aspect-video bg-gray-900 rounded-lg flex items-center justify-center">
                  <img 
                    src={selectedMedia.file_path} 
                    alt={selectedMedia.file_name}
                    className="max-w-full max-h-full object-contain rounded-lg"
                  />
                </div>
              ) : selectedMedia.file_name.match(/\.(mp4|avi|mov|webm)$/i) ? (
                <div className="aspect-video bg-gray-900 rounded-lg">
                  <video 
                    src={selectedMedia.file_path}
                    controls
                    className="w-full h-full rounded-lg"
                  >
                    Your browser does not support video playback.
                  </video>
                </div>
              ) : selectedMedia.file_name.match(/\.(mp3|wav|ogg)$/i) ? (
                <div className="aspect-video bg-gray-900 rounded-lg flex items-center justify-center">
                  <div className="text-center">
                    <Music className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                    <audio 
                      src={selectedMedia.file_path}
                      controls
                      className="w-full max-w-md"
                    >
                      Your browser does not support audio playback.
                    </audio>
                  </div>
                </div>
              ) : (
                <div className="aspect-video bg-gray-900 rounded-lg flex items-center justify-center">
                  <div className="text-center">
                    {getMediaIcon(selectedMedia.file_name)}
                    <p className="text-gray-400 mt-2">Preview not available</p>
                    <button
                      onClick={() => handleDownloadMedia(selectedMedia.file_path, selectedMedia.file_name)}
                      className="mt-4 flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors mx-auto"
                    >
                      <Download className="w-4 h-4" />
                      Download File
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default UnifiedTicketsPage
