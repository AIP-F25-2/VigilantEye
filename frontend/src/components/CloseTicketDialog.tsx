import { useState, useEffect } from 'react'
import { CheckCircle, X } from 'lucide-react'
import { Button } from '@/components/Button'
import { TicketStatusBadge } from '@/components/TicketStatusBadge'
import { formatRelativeTime } from '@/utils/formatters'
import type { Ticket } from '@/types/ticket'

interface CloseTicketDialogProps {
  ticket: Ticket | null
  onConfirm: (reason?: string) => void
  onCancel: () => void
  isClosing: boolean
}

export function CloseTicketDialog({
  ticket,
  onConfirm,
  onCancel,
  isClosing,
}: CloseTicketDialogProps) {
  const [reason, setReason] = useState('')

  // Reset reason when ticket changes
  useEffect(() => {
    setReason('')
  }, [ticket])

  // Handle Escape key
  useEffect(() => {
    if (!ticket) return

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isClosing) {
        onCancel()
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('keydown', handleEscape)
    }
  }, [ticket, onCancel, isClosing])

  // Handle Ctrl+Enter for quick submit
  useEffect(() => {
    if (!ticket) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && !isClosing) {
        onConfirm(reason || undefined)
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [ticket, reason, onConfirm, isClosing])

  if (!ticket) {
    return null
  }

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-75 z-50 flex items-center justify-center p-4"
      onClick={onCancel}
      role="dialog"
      aria-modal="true"
      aria-labelledby="dialog-title"
    >
      <div
        className="bg-white rounded-lg max-w-md w-full"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center">
            <CheckCircle className="h-6 w-6 text-green-600 mr-3" />
            <h2 id="dialog-title" className="text-xl font-semibold text-gray-900">
              Close Ticket?
            </h2>
          </div>
          <button
            onClick={onCancel}
            disabled={isClosing}
            className="text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500 rounded"
            aria-label="Close dialog"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4">
          <p className="text-gray-600">Mark this incident as resolved</p>

          {/* Ticket Details */}
          <div className="bg-gray-50 rounded-md p-4 space-y-2">
            <p className="text-sm font-medium text-gray-900">Ticket Details:</p>
            <div className="text-sm text-gray-600 space-y-1">
              <p>
                <span className="font-medium">Ticket ID:</span> {ticket.id.substring(0, 8)}
              </p>
              <p>
                <span className="font-medium">Title:</span> {ticket.title}
              </p>
              <p>
                <span className="font-medium">Status:</span>{' '}
                <TicketStatusBadge status={ticket.status} />
              </p>
              <p>
                <span className="font-medium">Created:</span> {formatRelativeTime(ticket.created_at)}
              </p>
            </div>
          </div>

          <p className="text-sm text-gray-600">
            This ticket will be marked as closed and removed from active tickets.
          </p>

          {/* Reason Input */}
          <div>
            <label htmlFor="close-reason" className="block text-sm font-medium text-gray-700 mb-1">
              Closure Reason (Recommended)
            </label>
            <textarea
              id="close-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g., False alarm, Issue resolved, Suspect apprehended, etc."
              maxLength={500}
              disabled={isClosing}
              rows={3}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm disabled:bg-gray-100 disabled:cursor-not-allowed px-3 py-2 border"
              autoFocus
            />
            <p className="mt-1 text-xs text-gray-500">{reason.length}/500 characters</p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200">
          <Button onClick={onCancel} variant="secondary" disabled={isClosing}>
            Cancel
          </Button>
          <Button
            onClick={() => onConfirm(reason || undefined)}
            variant="primary"
            isLoading={isClosing}
            disabled={isClosing}
            className="bg-green-600 hover:bg-green-700"
          >
            Close Ticket
          </Button>
        </div>
      </div>
    </div>
  )
}

