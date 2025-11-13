import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface TopCamerasChartProps {
  data: Array<{
    camera_id: string
    camera_name: string
    incident_count: number
  }>
  isLoading?: boolean
  height?: number
  maxCameras?: number
}

interface CustomTooltipProps {
  active?: boolean
  payload?: Array<{
    payload: {
      name: string
      incidents: number
      fullName: string
    }
  }>
}

const CustomTooltip = ({ active, payload }: CustomTooltipProps) => {
  if (active && payload && payload.length > 0) {
    const data = payload[0].payload
    return (
      <div className="bg-white p-3 border border-gray-200 rounded-md shadow-md">
        <p className="font-medium">{data.fullName}</p>
        <p className="text-sm text-gray-600">{data.incidents} incidents</p>
      </div>
    )
  }
  return null
}

export function TopCamerasChart({
  data,
  isLoading = false,
  height = 300,
  maxCameras = 10,
}: TopCamerasChartProps) {
  if (isLoading) {
    return (
      <div className="animate-pulse bg-gray-200 rounded" style={{ height }} />
    )
  }

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center text-gray-500" style={{ height }}>
        No camera data available
      </div>
    )
  }

  const sortedData = [...data].sort((a, b) => b.incident_count - a.incident_count)
  const topCameras = sortedData.slice(0, maxCameras)

  const chartData = topCameras.map((d) => ({
    name: d.camera_name.length > 20 ? d.camera_name.substring(0, 20) + '...' : d.camera_name,
    incidents: d.incident_count,
    fullName: d.camera_name,
  }))

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          dataKey="name"
          angle={-45}
          textAnchor="end"
          height={80}
          tick={{ fontSize: 11 }}
        />
        <YAxis
          tick={{ fontSize: 12 }}
          label={{ value: 'Incidents', angle: -90, position: 'insideLeft' }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="incidents" fill="#0ea5e9" radius={[8, 8, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

