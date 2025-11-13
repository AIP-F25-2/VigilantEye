import api from './api'
import type { HealthResponse, ReadinessResponse, MetricsResponse } from '@/types/analytics'

export const healthService = {
  async getHealth(): Promise<HealthResponse> {
    const response = await api.get<HealthResponse>('/health')
    return response.data
  },

  async getReadiness(): Promise<ReadinessResponse> {
    const response = await api.get<ReadinessResponse>('/health/ready')
    return response.data
  },

  async getMetrics(): Promise<MetricsResponse> {
    const response = await api.get<MetricsResponse>('/api/metrics')
    return response.data
  },
}

