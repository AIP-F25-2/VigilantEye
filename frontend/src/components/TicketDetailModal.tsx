import { useState, useEffect, useCallback } from 'react'
import { X, Loader2, CheckCircle, XCircle, AlertTriangle, Download, FileText } from 'lucide-react'
import { ticketService } from '@/services/ticketService'
import { Button } from '@/components/Button'
import { TicketStatusBadge } from '@/components/TicketStatusBadge'
import { PriorityBadge } from '@/components/PriorityBadge'
import { ThreatLevelBadge } from '@/components/ThreatLevelBadge'
import { EvidenceGallery } from '@/components/EvidenceGallery'
import { PersonCard } from '@/components/PersonCard'
import { TicketTimeline } from '@/components/TicketTimeline'
import { TTLCountdown } from '@/components/TTLCountdown'
import { formatRelativeTime, formatDate } from '@/utils/formatters'
import toast from 'react-hot-toast'
import type { Ticket, TicketDetailResponse } from '@/types/ticket'

interface TicketDetailModalProps {
  ticket: Ticket | null
  onClose: () => void
  onAcknowledge?: (ticketId: string) => void
  onCloseTicket?: (ticket: Ticket) => void
  onEscalate?: (ticketId: string) => void
  onDownloadReport?: (ticketId: string) => Promise<void>
}

type TabType = 'overview' | 'evidence' | 'ai_analysis' | 'persons' | 'timeline'

export function TicketDetailModal({
  ticket,
  onClose,
  onAcknowledge,
  onCloseTicket,
  onEscalate,
  onDownloadReport,
}: TicketDetailModalProps) {
  const [ticketDetails, setTicketDetails] = useState<TicketDetailResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<TabType>('overview')
  const [expandedReasoning, setExpandedReasoning] = useState(false)

  const fetchTicketDetails = useCallback(async () => {
    if (!ticket) return

    setIsLoading(true)
    setError(null)

    try {
      const details = await ticketService.getTicketDetails(ticket.id)
      setTicketDetails(details)
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || err.message || 'Failed to load ticket details'
      setError(errorMessage)
      toast.error(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }, [ticket])

  useEffect(() => {
    if (!ticket) {
      setTicketDetails(null)
      setError(null)
      setIsLoading(false)
      setActiveTab('overview')
      return
    }

    fetchTicketDetails()
  }, [ticket, fetchTicketDetails])

  // Handle Escape key to close modal
  useEffect(() => {
    if (!ticket) return

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('keydown', handleEscape)
    }
  }, [ticket, onClose])

  if (!ticket) {
    return null
  }

  const handleDownloadReport = async () => {
    if (!onDownloadReport) return
    try {
      await onDownloadReport(ticket.id)
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || err.message || 'Failed to download report'
      toast.error(errorMessage)
    }
  }

  const tabs: Array<{ id: TabType; label: string }> = [
    { id: 'overview', label: 'Overview' },
    { id: 'evidence', label: 'Evidence' },
    { id: 'ai_analysis', label: 'AI Analysis' },
    { id: 'persons', label: 'Persons' },
    { id: 'timeline', label: 'Timeline' },
  ]

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-75 z-50 flex items-center justify-center p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div
        className="bg-white rounded-lg max-w-6xl w-full max-h-[90vh] overflow-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 z-10 p-6">
          <div className="flex items-start justify-between mb-4">
            <div className="flex-1 min-w-0">
              <h2 id="modal-title" className="text-xl font-semibold text-gray-900 truncate">
                {ticket.title}
              </h2>
              <div className="mt-2 flex flex-wrap gap-3 items-center">
                <span className="text-xs font-mono text-gray-500">ID: {ticket.id.substring(0, 8)}</span>
                <TicketStatusBadge status={ticket.status} />
                <PriorityBadge priority={ticket.priority} />
                <ThreatLevelBadge threatLevel={ticket.threat_level} />
                {ticket.auto_close_at && <TTLCountdown expiresAt={ticket.auto_close_at} />}
              </div>
            </div>
            <button
              onClick={onClose}
              className="ml-4 text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500 rounded"
              aria-label="Close modal"
            >
              <X className="h-6 w-6" />
            </button>
          </div>

          {/* Tab Navigation */}
          <div className="flex gap-1 border-b border-gray-200 -mb-px overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap
                  ${
                    activeTab === tab.id
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Body */}
        <div className="p-6">
          {isLoading && (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="h-12 w-12 text-primary-600 animate-spin mb-4" />
              <p className="text-gray-600">Loading ticket details...</p>
            </div>
          )}

          {error && (
            <div className="flex flex-col items-center justify-center py-12">
              <p className="text-red-600 mb-4">{error}</p>
              <Button onClick={fetchTicketDetails}>Retry</Button>
            </div>
          )}

          {ticketDetails && !isLoading && !error && (
            <>
              {/* Overview Tab */}
              {activeTab === 'overview' && (
                <div className="space-y-6">
                  {/* Ticket Information */}
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Ticket Information</h3>
                    <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-gray-600">ID:</span>
                          <span className="ml-2 font-mono text-gray-900">{ticket.id}</span>
                        </div>
                        <div>
                          <span className="text-gray-600">Status:</span>
                          <span className="ml-2">
                            <TicketStatusBadge status={ticket.status} />
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-600">Priority:</span>
                          <span className="ml-2">
                            <PriorityBadge priority={ticket.priority} />
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-600">Threat Level:</span>
                          <span className="ml-2">
                            <ThreatLevelBadge threatLevel={ticket.threat_level} />
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-600">Created:</span>
                          <span className="ml-2 text-gray-900">{formatRelativeTime(ticket.created_at)}</span>
                        </div>
                        {ticket.acknowledged_at && (
                          <div>
                            <span className="text-gray-600">Acknowledged:</span>
                            <span className="ml-2 text-gray-900">
                              {formatRelativeTime(ticket.acknowledged_at)}
                            </span>
                          </div>
                        )}
                        {ticket.closed_at && (
                          <div>
                            <span className="text-gray-600">Closed:</span>
                            <span className="ml-2 text-gray-900">
                              {formatRelativeTime(ticket.closed_at)}
                            </span>
                          </div>
                        )}
                        {ticketDetails.assigned_user && (
                          <div>
                            <span className="text-gray-600">Assigned To:</span>
                            <span className="ml-2 text-gray-900">
                              {ticketDetails.assigned_user.username}
                            </span>
                          </div>
                        )}
                        {ticket.sla_breach && (
                          <div>
                            <span className="text-red-600 font-medium">SLA Breach:</span>
                            <span className="ml-2 text-red-600">Yes</span>
                          </div>
                        )}
                      </div>
                      {ticket.description && (
                        <div className="pt-3 border-t border-gray-200">
                          <span className="text-gray-600 text-sm">Description:</span>
                          <p className="mt-1 text-gray-900">{ticket.description}</p>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Video Information */}
                  {ticketDetails.video && (
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">Video Information</h3>
                      <div className="bg-gray-50 rounded-lg p-4 space-y-2 text-sm">
                        <p>
                          <span className="text-gray-600">Filename:</span>
                          <span className="ml-2 text-gray-900">{ticketDetails.video.filename}</span>
                        </p>
                        {ticketDetails.video.camera && (
                          <>
                            <p>
                              <span className="text-gray-600">Camera:</span>
                              <span className="ml-2 text-gray-900">
                                {ticketDetails.video.camera.name}
                              </span>
                            </p>
                            {ticketDetails.video.camera.location && (
                              <p>
                                <span className="text-gray-600">Location:</span>
                                <span className="ml-2 text-gray-900">
                                  {ticketDetails.video.camera.location}
                                </span>
                              </p>
                            )}
                          </>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Statistics */}
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Statistics</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="bg-gray-50 rounded-lg p-4 text-center">
                        <p className="text-2xl font-bold text-gray-900">
                          {ticketDetails.evidence.length}
                        </p>
                        <p className="text-sm text-gray-600">Evidence Items</p>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-4 text-center">
                        <p className="text-2xl font-bold text-gray-900">
                          {ticketDetails.persons_of_interest.length}
                        </p>
                        <p className="text-sm text-gray-600">Persons</p>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-4 text-center">
                        <p className="text-2xl font-bold text-gray-900">
                          {ticketDetails.history.length}
                        </p>
                        <p className="text-sm text-gray-600">History Events</p>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-4 text-center">
                        <p className="text-2xl font-bold text-gray-900">
                          {ticket.escalation_count}
                        </p>
                        <p className="text-sm text-gray-600">Escalations</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Evidence Tab */}
              {activeTab === 'evidence' && (
                <div>
                  <EvidenceGallery evidence={ticketDetails.evidence} ticketId={ticket.id} />
                </div>
              )}

              {/* AI Analysis Tab */}
              {activeTab === 'ai_analysis' && (() => {
                // Extract LLM reasoning from evidence ai_analysis or use ticket description as fallback
                const llmReasoning = ticketDetails.evidence
                  .map((e) => {
                    if (e.ai_analysis && typeof e.ai_analysis === 'object') {
                      return e.ai_analysis.llm_reasoning || 
                             (e.ai_analysis.reasoning ? (typeof e.ai_analysis.reasoning === 'string' ? e.ai_analysis.reasoning : e.ai_analysis.reasoning.reasoning || '') : null)
                    }
                    return null
                  })
                  .find((r) => r) || ticket.description || 'No reasoning available'
                
                return (
                  <div className="space-y-6">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">LLM Assessment</h3>
                      <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                        <div>
                          <span className="text-sm font-medium text-gray-700">Reasoning:</span>
                          <p className="mt-1 text-gray-900 whitespace-pre-wrap">
                            {llmReasoning && llmReasoning.length > 200 && !expandedReasoning
                              ? `${llmReasoning.substring(0, 200)}...`
                              : llmReasoning}
                          </p>
                          {llmReasoning && llmReasoning.length > 200 && (
                            <button
                              onClick={() => setExpandedReasoning(!expandedReasoning)}
                              className="mt-2 text-sm text-primary-600 hover:text-primary-700"
                            >
                              {expandedReasoning ? 'Read less' : 'Read more'}
                            </button>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* AI Module Outputs */}
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">AI Module Outputs</h3>
                      <div className="space-y-4">
                        {ticketDetails.evidence
                          .filter((e) => e.ai_analysis)
                          .map((evidence) => (
                            <div key={evidence.id} className="bg-gray-50 rounded-lg p-4">
                              <p className="font-medium text-gray-900 mb-2">
                                Evidence #{evidence.id.substring(0, 8)}
                              </p>
                              <pre className="text-xs text-gray-700 whitespace-pre-wrap font-sans">
                                {JSON.stringify(evidence.ai_analysis, null, 2)}
                              </pre>
                            </div>
                          ))}
                        {ticketDetails.evidence.filter((e) => e.ai_analysis).length === 0 && (
                          <p className="text-gray-500 text-sm">No AI analysis data available</p>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })()}

              {/* Persons Tab */}
              {activeTab === 'persons' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">
                      Persons of Interest ({ticketDetails.persons_of_interest.length})
                    </h3>
                    {ticketDetails.persons_of_interest.length === 0 ? (
                      <p className="text-gray-500 text-sm">No persons of interest detected</p>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {ticketDetails.persons_of_interest.map((person) => (
                          <div key={person.id}>
                            <PersonCard person={person} />
                            {person.similar_persons && person.similar_persons.length > 0 && (
                              <div className="mt-4">
                                <h4 className="text-sm font-medium text-gray-700 mb-2">
                                  Similar Persons for {person.person_tracking_id.substring(0, 8)}
                                </h4>
                                <div className="grid grid-cols-2 gap-2">
                                  {person.similar_persons.map((similar, idx) => (
                                    <PersonCard
                                      key={idx}
                                      person={similar.person}
                                      similarityScore={similar.similarity}
                                      compact
                                    />
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Timeline Tab */}
              {activeTab === 'timeline' && (
                <div>
                  <TicketTimeline history={ticketDetails.history} />
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        {ticketDetails && !isLoading && !error && (
          <div className="sticky bottom-0 bg-white border-t border-gray-200 p-6 flex items-center justify-end gap-3">
            {ticket.status === 'open' && onAcknowledge && (
              <Button onClick={() => onAcknowledge(ticket.id)} variant="primary">
                <CheckCircle className="mr-2 h-4 w-4" />
                Acknowledge
              </Button>
            )}
            {ticket.status !== 'closed' && onCloseTicket && (
              <Button onClick={() => onCloseTicket(ticket)} variant="primary" className="bg-green-600 hover:bg-green-700">
                <XCircle className="mr-2 h-4 w-4" />
                Close
              </Button>
            )}
            {!ticket.escalated && onEscalate && (
              <Button onClick={() => onEscalate(ticket.id)} variant="secondary">
                <AlertTriangle className="mr-2 h-4 w-4" />
                Escalate
              </Button>
            )}
            {onDownloadReport && (
              <Button onClick={handleDownloadReport} variant="secondary">
                <Download className="mr-2 h-4 w-4" />
                Download Report
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

