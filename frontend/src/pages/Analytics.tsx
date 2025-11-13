import { useState, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Activity,
  BarChart3,
  Database,
  HardDrive,
  Cpu,
  Zap,
  RefreshCw,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { subDays } from 'date-fns'
import { useAuth } from '@/hooks/useAuth'
import { healthService } from '@/services/healthService'
import { analyticsService } from '@/services/analyticsService'
import { Button } from '@/components/Button'
import { HealthMetricsCard } from '@/components/HealthMetricsCard'
import { DateRangeSelector } from '@/components/DateRangeSelector'
import { TicketsOverTimeChart } from '@/components/charts/TicketsOverTimeChart'
import { ThreatDistributionChart } from '@/components/charts/ThreatDistributionChart'
import { ResponseTimeChart } from '@/components/charts/ResponseTimeChart'
import { TopCamerasChart } from '@/components/charts/TopCamerasChart'
import { formatRelativeTime, formatLatency } from '@/utils/formatters'
import type { DateRange } from '@/types/analytics'

const REFRESH_INTERVAL = 30000

export default function AnalyticsPage() {
  const { user } = useAuth()
  const [dateRange, setDateRange] = useState<DateRange | null>({
    from: subDays(new Date(), 1),
    to: new Date(),
  })
  const [isAutoRefreshEnabled, setIsAutoRefreshEnabled] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date())

  // React Query: Health Data (Auto-Refresh Every 30s)
  const {
    data: healthData,
    isLoading: isLoadingHealth,
    error: healthError,
    refetch: refetchHealth,
  } = useQuery({
    queryKey: ['health'],
    queryFn: healthService.getHealth,
    refetchInterval: isAutoRefreshEnabled ? REFRESH_INTERVAL : false,
    staleTime: REFRESH_INTERVAL,
    onSuccess: () => setLastUpdated(new Date()),
  })

  // React Query: Metrics Data (Auto-Refresh Every 30s)
  const {
    data: metricsData,
    isLoading: isLoadingMetrics,
    error: metricsError,
    refetch: refetchMetrics,
  } = useQuery({
    queryKey: ['metrics'],
    queryFn: healthService.getMetrics,
    refetchInterval: isAutoRefreshEnabled ? REFRESH_INTERVAL : false,
    staleTime: REFRESH_INTERVAL,
  })

  // React Query: Analytics Data (Auto-Refresh Every 30s, Filtered by Date Range)
  const {
    data: analyticsData,
    isLoading: isLoadingAnalytics,
    error: analyticsError,
    refetch: refetchAnalytics,
  } = useQuery({
    queryKey: ['analytics', dateRange],
    queryFn: () => analyticsService.getTicketAnalytics(dateRange),
    refetchInterval: isAutoRefreshEnabled ? REFRESH_INTERVAL : false,
    staleTime: REFRESH_INTERVAL,
  })

  // Manual Refresh Handler
  const handleRefresh = useCallback(() => {
    refetchHealth()
    refetchMetrics()
    refetchAnalytics()
    toast.success('Data refreshed')
  }, [refetchHealth, refetchMetrics, refetchAnalytics])

  // Calculate average AI inference time
  const calculateAvgInference = (aiInferenceTimes: any) => {
    if (!aiInferenceTimes) return undefined
    const times = Object.values(aiInferenceTimes) as number[]
    const sum = times.reduce((acc, val) => acc + val, 0)
    return Math.round(sum / times.length)
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      {/* Page Header */}
      <div className="mb-8">
        <div className="flex items-center mb-2">
          <BarChart3 className="h-8 w-8 text-primary-600 mr-2" />
          <h1 className="text-3xl font-bold text-gray-900">Analytics Dashboard</h1>
        </div>
        <p className="text-gray-600">System health monitoring and security analytics</p>
      </div>

      {/* Controls Row */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600">
            Last updated: {formatRelativeTime(lastUpdated.toISOString())}
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsAutoRefreshEnabled(!isAutoRefreshEnabled)}
          >
            {isAutoRefreshEnabled ? 'Pause' : 'Resume'} Auto-Refresh
          </Button>
          <Button variant="secondary" size="sm" onClick={handleRefresh}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
        <DateRangeSelector value={dateRange} onChange={setDateRange} />
      </div>

      {/* Section 1: System Health */}
      <div className="mb-8">
        <div className="flex items-center mb-4">
          <Activity className="h-6 w-6 text-primary-600 mr-2" />
          <h2 className="text-2xl font-bold text-gray-900">System Health</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <HealthMetricsCard
            title="API Latency (p95)"
            value={metricsData?.api_latency.p95 ? formatLatency(metricsData.api_latency.p95) : undefined}
            status={
              metricsData?.api_latency.p95 && metricsData.api_latency.p95 < 500
                ? 'healthy'
                : 'warning'
            }
            icon={<Zap className="w-6 h-6 text-green-600" />}
          />
          <HealthMetricsCard
            title="Database"
            value={healthData?.database.status}
            status={healthData?.database.status === 'connected' ? 'healthy' : 'error'}
            icon={<Database className="w-6 h-6 text-green-600" />}
          />
          <HealthMetricsCard
            title="Storage Usage"
            value={healthData?.storage.percentage}
            unit="%"
            status={
              healthData?.storage.percentage && healthData.storage.percentage < 80
                ? 'healthy'
                : 'warning'
            }
            icon={<HardDrive className="w-6 h-6 text-green-600" />}
          />
          <HealthMetricsCard
            title="Celery Workers"
            value={healthData?.celery.workers}
            status={healthData?.celery.workers && healthData.celery.workers > 0 ? 'healthy' : 'error'}
            icon={<Cpu className="w-6 h-6 text-green-600" />}
          />
          <HealthMetricsCard
            title="AI Inference (Avg)"
            value={metricsData?.ai_inference_times ? formatLatency(calculateAvgInference(metricsData.ai_inference_times) || 0) : undefined}
            status="healthy"
            icon={<Activity className="w-6 h-6 text-green-600" />}
          />
          <HealthMetricsCard
            title="Redis"
            value={healthData?.redis.status}
            status={healthData?.redis.status === 'connected' ? 'healthy' : 'error'}
            icon={<Database className="w-6 h-6 text-green-600" />}
          />
        </div>
        {healthError && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-600">Unable to fetch health data</p>
            <Button onClick={() => refetchHealth()} variant="primary" size="sm" className="mt-2">
              Retry
            </Button>
          </div>
        )}
      </div>

      {/* Section 2: Security Analytics */}
      <div className="mb-8">
        <div className="flex items-center mb-4">
          <BarChart3 className="h-6 w-6 text-primary-600 mr-2" />
          <h2 className="text-2xl font-bold text-gray-900">Security Analytics</h2>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Chart 1: Tickets Over Time */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Tickets Over Time</h3>
            <TicketsOverTimeChart
              data={analyticsData?.tickets_over_time || []}
              isLoading={isLoadingAnalytics}
            />
          </div>

          {/* Chart 2: Threat Distribution */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Threat Distribution</h3>
            <ThreatDistributionChart
              data={analyticsData?.threat_distribution || []}
              isLoading={isLoadingAnalytics}
            />
          </div>

          {/* Chart 3: Response Time Metrics */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Response Time Metrics</h3>
            <ResponseTimeChart
              data={metricsData?.api_latency}
              isLoading={isLoadingMetrics}
            />
          </div>

          {/* Chart 4: Top Cameras by Incidents */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Cameras by Incidents</h3>
            <TopCamerasChart
              data={analyticsData?.top_cameras || []}
              isLoading={isLoadingAnalytics}
              maxCameras={10}
            />
          </div>
        </div>
        {analyticsError && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-600">Unable to fetch analytics data</p>
            <Button onClick={() => refetchAnalytics()} variant="primary" size="sm" className="mt-2">
              Retry
            </Button>
          </div>
        )}
      </div>

      {/* Section 3: AI Performance Metrics */}
      {metricsData?.ai_inference_times && (
        <div className="mb-8">
          <div className="flex items-center mb-4">
            <Activity className="h-6 w-6 text-primary-600 mr-2" />
            <h2 className="text-2xl font-bold text-gray-900">AI Model Performance</h2>
          </div>
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600 mb-1">Person Detection</p>
                <p className="text-2xl font-bold text-gray-900">
                  {formatLatency(metricsData.ai_inference_times.person_detection)}
                </p>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600 mb-1">Scene Analysis</p>
                <p className="text-2xl font-bold text-gray-900">
                  {formatLatency(metricsData.ai_inference_times.scene_analysis)}
                </p>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600 mb-1">Object Detection</p>
                <p className="text-2xl font-bold text-gray-900">
                  {formatLatency(metricsData.ai_inference_times.object_detection)}
                </p>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600 mb-1">Speech-to-Text</p>
                <p className="text-2xl font-bold text-gray-900">
                  {formatLatency(metricsData.ai_inference_times.speech_to_text)}
                </p>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600 mb-1">Audio Classification</p>
                <p className="text-2xl font-bold text-gray-900">
                  {formatLatency(metricsData.ai_inference_times.audio_classification)}
                </p>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600 mb-1">LLM Analysis</p>
                <p className="text-2xl font-bold text-gray-900">
                  {formatLatency(metricsData.ai_inference_times.llm_analysis)}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

