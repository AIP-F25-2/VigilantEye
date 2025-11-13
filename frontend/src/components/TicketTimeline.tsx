import { useState } from 'react'
import {
  Plus,
  CheckCircle,
  AlertTriangle,
  Lock,
  ArrowRight,
  UserPlus,
  AlertOctagon,
  Clock,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { cn } from '@/utils/cn'
import type { TicketHistory } from '@/types/ticket'

interface TicketTimelineProps {
  history: TicketHistory[]
}

export function TicketTimeline({ history }: TicketTimelineProps) {
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set())

  const toggleEvent = (eventId: string) => {
    setExpandedEvents((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(eventId)) {
        newSet.delete(eventId)
      } else {
        newSet.add(eventId)
      }
      return newSet
    })
  }

  const getEventConfig = (event: string) => {
    const eventLower = event.toLowerCase()
    if (eventLower.includes('created')) {
      return {
        icon: Plus,
        color: 'bg-blue-500',
        text: 'Ticket Created',
      }
    }
    if (eventLower.includes('acknowledged')) {
      return {
        icon: CheckCircle,
        color: 'bg-yellow-500',
        text: 'Acknowledged',
      }
    }
    if (eventLower.includes('escalated')) {
      if (eventLower.includes('auto')) {
        return {
          icon: AlertOctagon,
          color: 'bg-red-500',
          text: 'Auto-Escalated (SLA Breach)',
        }
      }
      return {
        icon: AlertTriangle,
        color: 'bg-orange-500',
        text: 'Escalated',
      }
    }
    if (eventLower.includes('closed')) {
      if (eventLower.includes('auto')) {
        return {
          icon: Clock,
          color: 'bg-gray-500',
          text: 'Auto-Closed',
        }
      }
      return {
        icon: Lock,
        color: 'bg-gray-500',
        text: 'Closed',
      }
    }
    if (eventLower.includes('status_changed') || eventLower.includes('status changed')) {
      return {
        icon: ArrowRight,
        color: 'bg-purple-500',
        text: 'Status Changed',
      }
    }
    if (eventLower.includes('assigned')) {
      return {
        icon: UserPlus,
        color: 'bg-green-500',
        text: 'Assigned',
      }
    }
    return {
      icon: Clock,
      color: 'bg-gray-500',
      text: event,
    }
  }

  if (history.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>No history available</p>
      </div>
    )
  }

  // Sort by occurred_at ascending (oldest first)
  const sortedHistory = [...history].sort(
    (a, b) => new Date(a.occurred_at).getTime() - new Date(b.occurred_at).getTime()
  )

  return (
    <div className="relative">
      {/* Timeline line */}
      <div className="absolute left-2 top-0 bottom-0 w-0.5 bg-gray-300" />

      <div className="space-y-4">
        {sortedHistory.map((entry, index) => {
          const config = getEventConfig(entry.event)
          const Icon = config.icon
          const isExpanded = expandedEvents.has(entry.id)
          const hasDetails = entry.details && Object.keys(entry.details).length > 0

          return (
            <div key={entry.id} className="relative flex items-start">
              {/* Timeline dot */}
              <div className="relative z-10 flex items-center justify-center w-4 h-4 rounded-full bg-white border-2 border-gray-300">
                <div className={cn('w-2 h-2 rounded-full', config.color)} />
              </div>

              {/* Event card */}
              <div className="ml-6 flex-1 mb-4">
                <div
                  className={cn(
                    'bg-gray-50 rounded-lg p-3 hover:shadow-md transition-shadow cursor-pointer',
                    hasDetails && 'cursor-pointer'
                  )}
                  onClick={() => hasDetails && toggleEvent(entry.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2 flex-1">
                      <Icon className={cn('h-5 w-5', config.color.replace('bg-', 'text-'))} />
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">{config.text}</p>
                        <p className="text-sm text-gray-600">
                          {formatDistanceToNow(new Date(entry.occurred_at), { addSuffix: true })}
                        </p>
                        {entry.user_id && (
                          <p className="text-xs text-gray-500 mt-1">by user {entry.user_id.substring(0, 8)}</p>
                        )}
                      </div>
                    </div>
                    {hasDetails && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          toggleEvent(entry.id)
                        }}
                        className="text-gray-400 hover:text-gray-600"
                      >
                        {isExpanded ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                      </button>
                    )}
                  </div>

                  {/* Expandable details */}
                  {isExpanded && hasDetails && (
                    <div className="mt-3 pt-3 border-t border-gray-200">
                      <pre className="text-xs text-gray-700 whitespace-pre-wrap font-sans">
                        {JSON.stringify(entry.details, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

