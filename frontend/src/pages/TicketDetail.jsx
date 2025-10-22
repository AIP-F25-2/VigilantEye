import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Clock,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Eye,
  Download,
  MessageSquare,
  User,
  Calendar,
  Video,
  Image,
  FileText,
  Trash2,
  Plus,
  Send,
  Shield,
} from 'lucide-react'
import Logo from '../components/Logo'
import { useAuthStore } from '../store/authStore'
import { ticketAPI } from '../services/api'

const TicketDetail = () => {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user, clearAuth } = useAuthStore()
  
  const [ticket, setTicket] = useState(null)
  const [evidence, setEvidence] = useState([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [showNoteModal, setShowNoteModal] = useState(false)
  const [noteText, setNoteText] = useState('')
  const [selectedImage, setSelectedImage] = useState(null)

  const loadTicket = async () => {
    try {
      setLoading(true)
      const [ticketData, evidenceData] = await Promise.all([
        ticketAPI.getTicket(id),
        ticketAPI.getTicketEvidence(id)
      ])
      setTicket(ticketData)
      setEvidence(evidenceData)
    } catch (error) {
      console.error('Failed to load ticket:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTicket()
  }, [id])

  const handleLogout = () => {
    clearAuth()
    navigate('/login')
  }

  const handleAcknowledge = async () => {
    try {
      setActionLoading(true)
      await ticketAPI.acknowledgeTicket(id)
      await loadTicket()
    } catch (error) {
      console.error('Failed to acknowledge ticket:', error)
    } finally {
      setActionLoading(false)
    }
  }

  const handleClose = async () => {
    try {
      setActionLoading(true)
      await ticketAPI.closeTicket(id)
      await loadTicket()
    } catch (error) {
      console.error('Failed to close ticket:', error)
    } finally {
      setActionLoading(false)
    }
  }

  const handleAddNote = async () => {
    if (!noteText.trim()) return
    
    try {
      setActionLoading(true)
      await ticketAPI.addNote(id, noteText)
      setNoteText('')
      setShowNoteModal(false)
      await loadTicket()
    } catch (error) {
      console.error('Failed to add note:', error)
    } finally {
      setActionLoading(false)
    }
  }

  const handleDeleteEvidence = async (evidenceId) => {
    if (!confirm('Are you sure you want to delete this evidence file?')) return
    
    try {
      await ticketAPI.deleteEvidence(id, evidenceId)
      await loadTicket()
    } catch (error) {
      console.error('Failed to delete evidence:', error)
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'OPEN':
        return <Clock className="w-5 h-5 text-yellow-500" />
      case 'ACKNOWLEDGED':
        return <CheckCircle className="w-5 h-5 text-blue-500" />
      case 'ESCALATED':
        return <AlertTriangle className="w-5 h-5 text-red-500" />
      case 'CLOSED':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'AUTO_CLOSED':
        return <XCircle className="w-5 h-5 text-gray-500" />
      default:
        return <Clock className="w-5 h-5 text-gray-500" />
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

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
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

    if (diffMins < 60) return `${diffMins} minutes ago`
    if (diffHours < 24) return `${diffHours} hours ago`
    return `${diffDays} days ago`
  }

  const canAcknowledge = ticket?.status === 'OPEN' || ticket?.status === 'ESCALATED'
  const canClose = ticket?.status !== 'CLOSED' && ticket?.status !== 'AUTO_CLOSED'

  if (loading) {
    return (
      <div className="min-h-screen bg-dark-950 grid-bg flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500 mx-auto mb-4"></div>
          <p className="text-gray-400">Loading ticket details...</p>
        </div>
      </div>
    )
  }

  if (!ticket) {
    return (
      <div className="min-h-screen bg-dark-950 grid-bg flex items-center justify-center">
        <div className="text-center">
          <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-200 mb-2">Ticket not found</h2>
          <p className="text-gray-400 mb-4">The ticket you're looking for doesn't exist.</p>
          <button
            onClick={() => navigate('/tickets')}
            className="btn-primary"
          >
            Back to Tickets
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-dark-950 grid-bg">
      {/* Header */}
      <header className="border-b border-gray-800 bg-dark-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate('/tickets')}
                className="flex items-center gap-2 px-3 py-2 text-gray-400 hover:text-white transition-colors rounded-lg hover:bg-dark-800"
              >
                <ArrowLeft className="w-4 h-4" />
                Back to Tickets
              </button>
              <Logo size="sm" />
            </div>
            
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

              {/* Logout Button */}
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg transition-colors border border-red-500/30"
              >
                <ArrowLeft className="w-4 h-4" />
                <span className="text-sm font-medium">Logout</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Ticket Header */}
        <div className="card-glass mb-6">
          <div className="flex items-start justify-between mb-6">
            <div className="flex items-center gap-4">
              {getStatusIcon(ticket.status)}
              <div>
                <h1 className="text-2xl font-bold text-gray-200 mb-2">
                  {ticket.title}
                </h1>
                <div className="flex items-center gap-3">
                  <span className="text-gray-400">{ticket.ticket_number}</span>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(ticket.status)}`}>
                    {ticket.status}
                  </span>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getPriorityColor(ticket.priority)}`}>
                    {ticket.priority}
                  </span>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-3">
              {canAcknowledge && (
                <button
                  onClick={handleAcknowledge}
                  disabled={actionLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50"
                >
                  <CheckCircle className="w-4 h-4" />
                  Acknowledge
                </button>
              )}
              
              {canClose && (
                <button
                  onClick={handleClose}
                  disabled={actionLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors disabled:opacity-50"
                >
                  <CheckCircle className="w-4 h-4" />
                  Close
                </button>
              )}
              
              <button
                onClick={() => setShowNoteModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-dark-800 hover:bg-dark-700 text-gray-300 rounded-lg transition-colors border border-gray-700"
              >
                <MessageSquare className="w-4 h-4" />
                Add Note
              </button>
            </div>
          </div>

          {/* Ticket Details */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="font-semibold text-gray-200 mb-3">Description</h3>
              <p className="text-gray-400 leading-relaxed">{ticket.description}</p>
            </div>

            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <Video className="w-4 h-4 text-gray-400" />
                <span className="text-gray-300">Video ID: {ticket.video_id}</span>
              </div>
              
              <div className="flex items-center gap-3">
                <Clock className="w-4 h-4 text-gray-400" />
                <span className="text-gray-300">Timestamp: {(ticket.frame_timestamp_ms / 1000).toFixed(2)}s</span>
              </div>
              
              <div className="flex items-center gap-3">
                <Calendar className="w-4 h-4 text-gray-400" />
                <span className="text-gray-300">Created: {formatDate(ticket.created_at)}</span>
              </div>
              
              {ticket.acknowledged_at && (
                <div className="flex items-center gap-3">
                  <CheckCircle className="w-4 h-4 text-blue-400" />
                  <span className="text-gray-300">Acknowledged: {formatTimeAgo(ticket.acknowledged_at)}</span>
                </div>
              )}
              
              {ticket.closed_at && (
                <div className="flex items-center gap-3">
                  <CheckCircle className="w-4 h-4 text-green-400" />
                  <span className="text-gray-300">Closed: {formatTimeAgo(ticket.closed_at)}</span>
                </div>
              )}
            </div>
          </div>

          {/* Notes */}
          {ticket.notes && (
            <div className="mt-6 pt-6 border-t border-gray-700">
              <h3 className="font-semibold text-gray-200 mb-3">Notes</h3>
              <div className="bg-dark-800 rounded-lg p-4">
                <pre className="text-gray-400 whitespace-pre-wrap">{ticket.notes}</pre>
              </div>
            </div>
          )}
        </div>

        {/* Evidence Gallery */}
        <div className="card-glass">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-200 flex items-center gap-2">
              <Image className="w-6 h-6 text-primary-500" />
              Evidence Gallery
            </h2>
            {evidence.length > 0 && (
              <button className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors">
                <Download className="w-4 h-4" />
                Download All
              </button>
            )}
          </div>

          {evidence.length === 0 ? (
            <div className="text-center py-12">
              <Image className="w-16 h-16 mx-auto mb-4 text-gray-600" />
              <h3 className="text-lg font-medium text-gray-300 mb-2">No evidence files</h3>
              <p className="text-gray-500">No evidence has been collected for this ticket yet.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {evidence.map((item) => (
                <div
                  key={item.id}
                  className="bg-dark-800 rounded-lg overflow-hidden border border-gray-700 hover:border-primary-500/50 transition-colors group"
                >
                  <div className="aspect-square bg-gray-900 flex items-center justify-center cursor-pointer"
                       onClick={() => setSelectedImage(item)}>
                    <Image className="w-8 h-8 text-gray-600 group-hover:text-primary-400 transition-colors" />
                  </div>
                  
                  <div className="p-4">
                    <h4 className="font-medium text-gray-200 mb-2 truncate">{item.file_name}</h4>
                    <div className="flex items-center justify-between text-xs text-gray-500">
                      <span className="capitalize">{item.evidence_type}</span>
                      {user?.role === 'ADMIN' && (
                        <button
                          onClick={() => handleDeleteEvidence(item.id)}
                          className="text-red-400 hover:text-red-300 transition-colors"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                    
                    {item.match_confidence && (
                      <div className="mt-2 text-xs text-primary-400">
                        Match: {(item.match_confidence * 100).toFixed(1)}%
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Note Modal */}
      {showNoteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-dark-800 rounded-lg p-6 w-full max-w-md border border-gray-700">
            <h3 className="text-lg font-semibold text-gray-200 mb-4">Add Note</h3>
            
            <textarea
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              placeholder="Enter your note..."
              className="w-full h-32 px-3 py-2 bg-dark-900 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:border-primary-500 focus:outline-none resize-none"
            />
            
            <div className="flex items-center gap-3 mt-6">
              <button
                onClick={() => {
                  setShowNoteModal(false)
                  setNoteText('')
                }}
                className="flex-1 px-4 py-2 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAddNote}
                disabled={!noteText.trim() || actionLoading}
                className="flex-1 btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {actionLoading ? 'Adding...' : 'Add Note'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Image Modal */}
      {selectedImage && (
        <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-50 p-4"
             onClick={() => setSelectedImage(null)}>
          <div className="max-w-4xl max-h-full bg-dark-800 rounded-lg overflow-hidden border border-gray-700">
            <div className="p-4 border-b border-gray-700 flex items-center justify-between">
              <h3 className="font-semibold text-gray-200">{selectedImage.file_name}</h3>
              <button
                onClick={() => setSelectedImage(null)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-4">
              <div className="aspect-video bg-gray-900 flex items-center justify-center">
                <Image className="w-16 h-16 text-gray-600" />
              </div>
              
              <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-400">Type:</span>
                  <span className="ml-2 text-gray-200 capitalize">{selectedImage.evidence_type}</span>
                </div>
                <div>
                  <span className="text-gray-400">File:</span>
                  <span className="ml-2 text-gray-200">{selectedImage.file_name}</span>
                </div>
                {selectedImage.match_confidence && (
                  <div>
                    <span className="text-gray-400">Match:</span>
                    <span className="ml-2 text-primary-400">{(selectedImage.match_confidence * 100).toFixed(1)}%</span>
                  </div>
                )}
                {selectedImage.description && (
                  <div className="col-span-2">
                    <span className="text-gray-400">Description:</span>
                    <span className="ml-2 text-gray-200">{selectedImage.description}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default TicketDetail
