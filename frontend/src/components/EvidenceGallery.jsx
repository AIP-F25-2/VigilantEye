import { useState } from 'react'
import {
  Image,
  Download,
  Trash2,
  Eye,
  X,
  ChevronLeft,
  ChevronRight,
  FileText,
  Video,
  Music,
  Archive,
} from 'lucide-react'

const EvidenceGallery = ({ 
  evidence = [], 
  onDelete, 
  canDelete = false,
  onDownloadAll 
}) => {
  const [selectedIndex, setSelectedIndex] = useState(null)
  const [viewMode, setViewMode] = useState('grid') // 'grid' or 'list'

  const getFileIcon = (evidenceType, fileName) => {
    const extension = fileName.split('.').pop().toLowerCase()
    
    if (evidenceType === 'original' || evidenceType === 'related_frame') {
      return <Image className="w-6 h-6 text-blue-500" />
    }
    
    switch (extension) {
      case 'jpg':
      case 'jpeg':
      case 'png':
      case 'gif':
      case 'webp':
        return <Image className="w-6 h-6 text-blue-500" />
      case 'mp4':
      case 'avi':
      case 'mov':
      case 'webm':
        return <Video className="w-6 h-6 text-purple-500" />
      case 'mp3':
      case 'wav':
      case 'ogg':
        return <Music className="w-6 h-6 text-green-500" />
      case 'pdf':
      case 'txt':
      case 'doc':
      case 'docx':
        return <FileText className="w-6 h-6 text-orange-500" />
      case 'zip':
      case 'rar':
      case '7z':
        return <Archive className="w-6 h-6 text-gray-500" />
      default:
        return <FileText className="w-6 h-6 text-gray-500" />
    }
  }

  const getFileTypeColor = (evidenceType, fileName) => {
    const extension = fileName.split('.').pop().toLowerCase()
    
    if (evidenceType === 'original' || evidenceType === 'related_frame') {
      return 'border-blue-500/30 bg-blue-500/10'
    }
    
    switch (extension) {
      case 'jpg':
      case 'jpeg':
      case 'png':
      case 'gif':
      case 'webp':
        return 'border-blue-500/30 bg-blue-500/10'
      case 'mp4':
      case 'avi':
      case 'mov':
      case 'webm':
        return 'border-purple-500/30 bg-purple-500/10'
      case 'mp3':
      case 'wav':
      case 'ogg':
        return 'border-green-500/30 bg-green-500/10'
      case 'pdf':
      case 'txt':
      case 'doc':
      case 'docx':
        return 'border-orange-500/30 bg-orange-500/10'
      case 'zip':
      case 'rar':
      case '7z':
        return 'border-gray-500/30 bg-gray-500/10'
      default:
        return 'border-gray-500/30 bg-gray-500/10'
    }
  }

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
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

  const handlePrevious = () => {
    setSelectedIndex(prev => prev > 0 ? prev - 1 : evidence.length - 1)
  }

  const handleNext = () => {
    setSelectedIndex(prev => prev < evidence.length - 1 ? prev + 1 : 0)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      setSelectedIndex(null)
    } else if (e.key === 'ArrowLeft') {
      handlePrevious()
    } else if (e.key === 'ArrowRight') {
      handleNext()
    }
  }

  if (evidence.length === 0) {
    return (
      <div className="text-center py-12">
        <Image className="w-16 h-16 mx-auto mb-4 text-gray-600" />
        <h3 className="text-lg font-medium text-gray-300 mb-2">No evidence files</h3>
        <p className="text-gray-500">No evidence has been collected for this ticket yet.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h2 className="text-xl font-semibold text-gray-200 flex items-center gap-2">
            <Image className="w-6 h-6 text-primary-500" />
            Evidence Gallery ({evidence.length} files)
          </h2>
          
          <div className="flex items-center gap-2">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 rounded-lg transition-colors ${
                viewMode === 'grid' 
                  ? 'bg-primary-600 text-white' 
                  : 'bg-dark-800 text-gray-400 hover:bg-dark-700'
              }`}
            >
              <Image className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 rounded-lg transition-colors ${
                viewMode === 'list' 
                  ? 'bg-primary-600 text-white' 
                  : 'bg-dark-800 text-gray-400 hover:bg-dark-700'
              }`}
            >
              <FileText className="w-4 h-4" />
            </button>
          </div>
        </div>

        {onDownloadAll && (
          <button 
            onClick={onDownloadAll}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
          >
            <Download className="w-4 h-4" />
            Download All
          </button>
        )}
      </div>

      {/* Grid View */}
      {viewMode === 'grid' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {evidence.map((item, index) => (
            <div
              key={item.id}
              className={`bg-dark-800 rounded-lg overflow-hidden border transition-colors group cursor-pointer ${getFileTypeColor(item.evidence_type, item.file_name)}`}
              onClick={() => setSelectedIndex(index)}
            >
              <div className="aspect-square bg-gray-900 flex items-center justify-center">
                {getFileIcon(item.evidence_type, item.file_name)}
              </div>
              
              <div className="p-4">
                <h4 className="font-medium text-gray-200 mb-2 truncate" title={item.file_name}>
                  {item.file_name}
                </h4>
                
                <div className="space-y-1 text-xs text-gray-500">
                  <div className="flex items-center justify-between">
                    <span className="capitalize">{item.evidence_type}</span>
                    {canDelete && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          onDelete?.(item.id)
                        }}
                        className="text-red-400 hover:text-red-300 transition-colors"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                  
                  {item.match_confidence && (
                    <div className="text-primary-400">
                      Match: {(item.match_confidence * 100).toFixed(1)}%
                    </div>
                  )}
                  
                  <div className="text-gray-400">
                    {formatDate(item.created_at)}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* List View */}
      {viewMode === 'list' && (
        <div className="space-y-2">
          {evidence.map((item, index) => (
            <div
              key={item.id}
              className={`bg-dark-800 rounded-lg p-4 border transition-colors group cursor-pointer hover:border-primary-500/50 ${getFileTypeColor(item.evidence_type, item.file_name)}`}
              onClick={() => setSelectedIndex(index)}
            >
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-gray-900 rounded-lg flex items-center justify-center">
                  {getFileIcon(item.evidence_type, item.file_name)}
                </div>
                
                <div className="flex-1 min-w-0">
                  <h4 className="font-medium text-gray-200 truncate" title={item.file_name}>
                    {item.file_name}
                  </h4>
                  <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
                    <span className="capitalize">{item.evidence_type}</span>
                    {item.match_confidence && (
                      <span className="text-primary-400">
                        Match: {(item.match_confidence * 100).toFixed(1)}%
                      </span>
                    )}
                    <span>{formatDate(item.created_at)}</span>
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setSelectedIndex(index)
                    }}
                    className="p-2 text-gray-400 hover:text-white transition-colors"
                  >
                    <Eye className="w-4 h-4" />
                  </button>
                  
                  {canDelete && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        onDelete?.(item.id)
                      }}
                      className="p-2 text-red-400 hover:text-red-300 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Lightbox Modal */}
      {selectedIndex !== null && (
        <div 
          className="fixed inset-0 bg-black/90 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedIndex(null)}
          onKeyDown={handleKeyDown}
          tabIndex={0}
        >
          <div className="max-w-6xl max-h-full bg-dark-800 rounded-lg overflow-hidden border border-gray-700">
            {/* Header */}
            <div className="p-4 border-b border-gray-700 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <span className="text-sm text-gray-400">
                  {selectedIndex + 1} of {evidence.length}
                </span>
                <h3 className="font-semibold text-gray-200 truncate">
                  {evidence[selectedIndex]?.file_name}
                </h3>
              </div>
              
              <div className="flex items-center gap-2">
                <button
                  onClick={handlePrevious}
                  className="p-2 text-gray-400 hover:text-white transition-colors"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <button
                  onClick={handleNext}
                  className="p-2 text-gray-400 hover:text-white transition-colors"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
                <button
                  onClick={() => setSelectedIndex(null)}
                  className="p-2 text-gray-400 hover:text-white transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>
            
            {/* Content */}
            <div className="p-4">
              <div className="aspect-video bg-gray-900 rounded-lg flex items-center justify-center mb-4">
                {getFileIcon(evidence[selectedIndex]?.evidence_type, evidence[selectedIndex]?.file_name)}
              </div>
              
              {/* Metadata */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-400">Type:</span>
                  <span className="ml-2 text-gray-200 capitalize">
                    {evidence[selectedIndex]?.evidence_type}
                  </span>
                </div>
                <div>
                  <span className="text-gray-400">File:</span>
                  <span className="ml-2 text-gray-200">
                    {evidence[selectedIndex]?.file_name}
                  </span>
                </div>
                {evidence[selectedIndex]?.match_confidence && (
                  <div>
                    <span className="text-gray-400">Match:</span>
                    <span className="ml-2 text-primary-400">
                      {(evidence[selectedIndex].match_confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                )}
                <div>
                  <span className="text-gray-400">Created:</span>
                  <span className="ml-2 text-gray-200">
                    {formatDate(evidence[selectedIndex]?.created_at)}
                  </span>
                </div>
                {evidence[selectedIndex]?.description && (
                  <div className="col-span-2">
                    <span className="text-gray-400">Description:</span>
                    <span className="ml-2 text-gray-200">
                      {evidence[selectedIndex].description}
                    </span>
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

export default EvidenceGallery
