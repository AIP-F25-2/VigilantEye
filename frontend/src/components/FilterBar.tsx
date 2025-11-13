import { useState, useEffect } from 'react'
import { Search, X } from 'lucide-react'
import { Button } from '@/components/Button'
import { useDebounce } from '@/hooks/useDebounce'
import type { VideoFilters } from '@/types/video'

interface FilterBarProps {
  filters: VideoFilters
  onFiltersChange: (filters: VideoFilters) => void
  onReset: () => void
  availableCameras?: string[]
}

export function FilterBar({ filters, onFiltersChange, onReset, availableCameras = [] }: FilterBarProps) {
  const [search, setSearch] = useState(filters.search || '')
  const [status, setStatus] = useState(filters.status || '')
  const [cameraId, setCameraId] = useState(filters.camera_id || '')
  const [uploadType, setUploadType] = useState(filters.upload_type || '')
  const [dateFrom, setDateFrom] = useState(filters.date_from || '')
  const [dateTo, setDateTo] = useState(filters.date_to || '')
  const [analysisResult, setAnalysisResult] = useState(filters.analysis_result || '')

  // Sync local state when filters prop changes (e.g., from reset)
  useEffect(() => {
    setSearch(filters.search || '')
    setStatus(filters.status || '')
    setCameraId(filters.camera_id || '')
    setUploadType(filters.upload_type || '')
    setDateFrom(filters.date_from || '')
    setDateTo(filters.date_to || '')
    setAnalysisResult(filters.analysis_result || '')
  }, [filters])

  // Debounce search input
  const debouncedSearch = useDebounce(search, 500)

  // Update filters when any filter value changes
  useEffect(() => {
    onFiltersChange({
      search: debouncedSearch || undefined,
      status: status || undefined,
      camera_id: cameraId || undefined,
      upload_type: uploadType || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      analysis_result: analysisResult || undefined,
    })
  }, [debouncedSearch, status, cameraId, uploadType, dateFrom, dateTo, analysisResult, onFiltersChange])

  const handleReset = () => {
    setSearch('')
    setStatus('')
    setCameraId('')
    setUploadType('')
    setDateFrom('')
    setDateTo('')
    setAnalysisResult('')
    onReset()
  }

  const hasActiveFilters =
    search || status || cameraId || uploadType || dateFrom || dateTo || analysisResult

  return (
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
              placeholder="Search videos..."
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
            <option value="uploading">Uploading</option>
            <option value="processing">Processing</option>
            <option value="ready">Ready</option>
            <option value="analyzing">Analyzing</option>
            <option value="analyzed">Analyzed</option>
            <option value="error">Error</option>
          </select>
        </div>

        {/* Camera Dropdown */}
        {availableCameras.length > 0 && (
          <div className="min-w-[150px]">
            <label htmlFor="camera" className="block text-sm font-medium text-gray-700 mb-1">
              Camera
            </label>
            <select
              id="camera"
              value={cameraId}
              onChange={(e) => setCameraId(e.target.value)}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm px-3 py-2 border"
            >
              <option value="">All</option>
              {availableCameras.map((camera) => (
                <option key={camera} value={camera}>
                  {camera}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Upload Type Dropdown */}
        <div className="min-w-[120px]">
          <label htmlFor="upload-type" className="block text-sm font-medium text-gray-700 mb-1">
            Type
          </label>
          <select
            id="upload-type"
            value={uploadType}
            onChange={(e) => setUploadType(e.target.value)}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm px-3 py-2 border"
          >
            <option value="">All</option>
            <option value="upload">Upload</option>
            <option value="stream">Stream</option>
          </select>
        </div>

        {/* Analysis Result Dropdown */}
        <div className="min-w-[150px]">
          <label htmlFor="analysis-result" className="block text-sm font-medium text-gray-700 mb-1">
            Analysis Result
          </label>
          <select
            id="analysis-result"
            value={analysisResult}
            onChange={(e) => setAnalysisResult(e.target.value)}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm px-3 py-2 border"
          >
            <option value="">All</option>
            <option value="pending">Pending</option>
            <option value="clean">Clean</option>
            <option value="suspicious">Suspicious</option>
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
            <Button onClick={handleReset} variant="ghost" size="md">
              <X className="mr-2 h-4 w-4" />
              Reset
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

