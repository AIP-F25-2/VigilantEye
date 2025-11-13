import { User } from 'lucide-react'
import { formatRelativeTime } from '@/utils/formatters'
import type { Person } from '@/types/ticket'

interface PersonCardProps {
  person: Person
  similarityScore?: number
  compact?: boolean
}

export function PersonCard({ person, similarityScore, compact = false }: PersonCardProps) {
  if (compact) {
    return (
      <div className="bg-white rounded-lg shadow-md p-3 hover:shadow-lg transition-shadow">
        <div className="relative">
          {person.thumbnail_path ? (
            <img
              src={person.thumbnail_path.startsWith('/') ? `/api${person.thumbnail_path}` : `/api/storage/${person.thumbnail_path}`}
              alt="Person"
              className="w-full h-32 object-cover rounded"
              onError={(e) => {
                const target = e.target as HTMLImageElement
                target.style.display = 'none'
                const fallback = target.nextElementSibling as HTMLElement
                if (fallback) fallback.style.display = 'flex'
              }}
            />
          ) : null}
          <div
            className="w-full h-32 bg-gray-200 rounded flex items-center justify-center"
            style={{ display: person.thumbnail_path ? 'none' : 'flex' }}
          >
            <User className="h-12 w-12 text-gray-400" />
          </div>
          {similarityScore !== undefined && (
            <span className="absolute top-2 right-2 bg-primary-600 text-white px-2 py-1 rounded text-xs font-medium">
              {Math.round(similarityScore * 100)}% match
            </span>
          )}
        </div>
        <div className="mt-2 space-y-1 text-sm">
          <p className="font-medium text-gray-900">
            ID: {person.person_tracking_id.substring(0, 8)}
          </p>
          {person.age_estimate && (
            <p className="text-gray-600">{person.age_estimate} years old</p>
          )}
          {person.gender && <p className="text-gray-600">{person.gender}</p>}
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-4 hover:shadow-lg transition-shadow">
      <div className="relative mb-4">
        {person.thumbnail_path ? (
          <img
            src={person.thumbnail_path.startsWith('/') ? `/api${person.thumbnail_path}` : `/api/storage/${person.thumbnail_path}`}
            alt="Person"
            className="w-full h-48 object-cover rounded"
            onError={(e) => {
              const target = e.target as HTMLImageElement
              target.style.display = 'none'
              const fallback = target.nextElementSibling as HTMLElement
              if (fallback) fallback.style.display = 'flex'
            }}
          />
        ) : null}
        <div
          className="w-full h-48 bg-gray-200 rounded flex items-center justify-center"
          style={{ display: person.thumbnail_path ? 'none' : 'flex' }}
        >
          <User className="h-16 w-16 text-gray-400" />
        </div>
        {similarityScore !== undefined && (
          <span className="absolute top-2 right-2 bg-primary-600 text-white px-2 py-1 rounded text-xs font-medium">
            {Math.round(similarityScore * 100)}% match
          </span>
        )}
      </div>

      <div className="space-y-3">
        <div>
          <p className="text-sm font-medium text-gray-900">
            Tracking ID: {person.person_tracking_id.substring(0, 8)}
          </p>
        </div>

        <div className="grid grid-cols-2 gap-2 text-sm">
          {person.age_estimate && (
            <div>
              <span className="text-gray-600">Age:</span>{' '}
              <span className="text-gray-900">{person.age_estimate} years</span>
            </div>
          )}
          {person.gender && (
            <div>
              <span className="text-gray-600">Gender:</span>{' '}
              <span className="text-gray-900">{person.gender}</span>
            </div>
          )}
          {person.ethnicity && (
            <div>
              <span className="text-gray-600">Ethnicity:</span>{' '}
              <span className="text-gray-900">{person.ethnicity}</span>
            </div>
          )}
          <div>
            <span className="text-gray-600">Confidence:</span>{' '}
            <span className="text-gray-900">
              {Math.round(person.confidence_score * 100)}%
            </span>
          </div>
        </div>

        {person.clothing_description && (
          <div>
            <span className="text-sm text-gray-600">Clothing:</span>
            <p className="text-sm text-gray-900">{person.clothing_description}</p>
          </div>
        )}

        <div className="pt-2 border-t border-gray-200 space-y-1 text-xs text-gray-600">
          <p>
            <span className="font-medium">First seen:</span>{' '}
            {formatRelativeTime(person.first_seen)}
          </p>
          <p>
            <span className="font-medium">Last seen:</span>{' '}
            {formatRelativeTime(person.last_seen)}
          </p>
          <p>
            <span className="font-medium">Appearances:</span> {person.total_appearances} time(s)
          </p>
        </div>
      </div>
    </div>
  )
}

