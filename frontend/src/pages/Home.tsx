import { useState, useEffect, useCallback, useRef } from 'react'
import { Eye, Upload, Camera, StopCircle, AlertCircle, CheckCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '@/hooks/useAuth'
import { useWebSocket } from '@/hooks/useWebSocket'
import { useLocalStreamSocket } from '@/hooks/useLocalStreamSocket'
import { videoService } from '@/services/videoService'
import { UploadZone } from '@/components/UploadZone'
import { Button } from '@/components/Button'
import { MAX_VIDEO_SIZE_MB, WS_NAMESPACE_ANALYSIS, MAX_CONCURRENT_STREAMS } from '@/utils/constants'
import type { Video, Stream, AnalysisCompleteEvent } from '@/types/video'
import type { AxiosError } from 'axios'

export default function HomePage() {
  const { user } = useAuth()
  const { socket, isConnected } = useWebSocket(WS_NAMESPACE_ANALYSIS)

  // Upload state
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  // Stream state
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamUrl, setStreamUrl] = useState('')
  const [cameraName, setCameraName] = useState('')
  const [currentCameraId, setCurrentCameraId] = useState<string | null>(null)
  const [activeStreams, setActiveStreams] = useState<Stream[]>([])
  const [maxStreams, setMaxStreams] = useState(MAX_CONCURRENT_STREAMS)
  
  // Local camera state
  const [cameraMode, setCameraMode] = useState<'rtsp' | 'local'>('rtsp')
  const [isLocalCameraActive, setIsLocalCameraActive] = useState(false)
  const [localCameraStream, setLocalCameraStream] = useState<MediaStream | null>(null)
  const [localStreamSessionId, setLocalStreamSessionId] = useState<string | null>(null)
  const [localVideoId, setLocalVideoId] = useState<string | null>(null)
  const [streamStats, setStreamStats] = useState({ fps: 0, framesSent: 0, bytesSent: 0 })
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationFrameRef = useRef<number | null>(null)
  const lastFrameTimeRef = useRef<number>(0)
  const statsIntervalRef = useRef<NodeJS.Timeout | null>(null)
  
  // Local stream WebSocket
  const { socket: localStreamSocket, isConnected: isLocalStreamConnected, connectionError: localStreamError, sendFrame, stopStream: stopLocalStreamSocket } = useLocalStreamSocket(localStreamSessionId)

  // Loading states
  const [isStartingStream, setIsStartingStream] = useState(false)
  const [isStoppingStream, setIsStoppingStream] = useState(false)
  const [isLoadingStreams, setIsLoadingStreams] = useState(false)

  // WebSocket: Listen for analysis_complete event
  useEffect(() => {
    if (!socket) return

    const handleAnalysisComplete = (data: AnalysisCompleteEvent) => {
      if (data.result === 'suspicious') {
        const ticketId = data.ticket_id?.substring(0, 8) || 'N/A'
        toast.error(`🚨 Suspicious activity detected! Ticket #${ticketId}`, {
          duration: 6000,
        })
      } else {
        toast.success('✅ No suspicious activity detected', {
          duration: 4000,
        })
      }
    }

    socket.on('analysis_complete', handleAnalysisComplete)

    return () => {
      socket.off('analysis_complete', handleAnalysisComplete)
    }
  }, [socket])

  // Fetch active streams on mount
  useEffect(() => {
    fetchActiveStreams()
  }, [])

  const fetchActiveStreams = useCallback(async () => {
    setIsLoadingStreams(true)
    try {
      const response = await videoService.getActiveStreams()
      setActiveStreams(response.active_streams)
      setMaxStreams(response.max_streams)
    } catch (error) {
      console.error('Failed to fetch active streams:', error)
    } finally {
      setIsLoadingStreams(false)
    }
  }, [])

  const handleFileSelect = useCallback(
    async (file: File) => {
      setSelectedFile(file)
      setIsUploading(true)
      setUploadProgress(0)

      try {
        const video = await videoService.uploadVideo(
          file,
          undefined,
          (progress) => setUploadProgress(progress)
        )
        toast.success(`Video uploaded successfully! ${video.filename}`)
        setSelectedFile(null)
        setUploadProgress(0)
      } catch (error) {
        const axiosError = error as AxiosError
        const message =
          axiosError.response?.data?.error || axiosError.message || 'Upload failed'
        toast.error(message)
      } finally {
        setIsUploading(false)
      }
    },
    []
  )

  const handleStartStream = useCallback(async () => {
    if (!streamUrl.trim()) {
      toast.error('Please enter stream URL')
      return
    }

    if (activeStreams.length >= maxStreams) {
      toast.error(`Maximum ${maxStreams} concurrent streams reached`)
      return
    }

    setIsStartingStream(true)
    try {
      const cameraId = `camera_${Date.now()}`
      const response = await videoService.startStream(
        cameraId,
        streamUrl,
        cameraName || undefined
      )
      // Use backend-returned camera_id
      setCurrentCameraId(response.camera_id)
      setIsStreaming(true)
      toast.success('Stream started successfully')
      await fetchActiveStreams()
    } catch (error) {
      const axiosError = error as AxiosError
      const message =
        axiosError.response?.data?.error || axiosError.message || 'Failed to start stream'
      toast.error(message)
    } finally {
      setIsStartingStream(false)
    }
  }, [streamUrl, cameraName, fetchActiveStreams, activeStreams.length, maxStreams])

  const handleStopStream = useCallback(async () => {
    if (!currentCameraId) return

    setIsStoppingStream(true)
    try {
      await videoService.stopStream(currentCameraId)
      setIsStreaming(false)
      setCurrentCameraId(null)
      setStreamUrl('')
      setCameraName('')
      toast.success('Stream stopped successfully')
      await fetchActiveStreams()
    } catch (error) {
      const axiosError = error as AxiosError
      const message =
        axiosError.response?.data?.error || axiosError.message || 'Failed to stop stream'
      toast.error(message)
    } finally {
      setIsStoppingStream(false)
    }
  }, [currentCameraId, fetchActiveStreams])

  const handleStartLocalCamera = useCallback(async () => {
    if (activeStreams.length >= maxStreams) {
      toast.error(`Maximum ${maxStreams} concurrent streams reached`)
      return
    }

    try {
      // Request camera access with mobile support
      const isMobile = /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
      const videoConstraints: MediaStreamConstraints = {
        video: {
          facingMode: isMobile ? 'user' : undefined,
          width: { ideal: 640 },
          height: { ideal: 480 },
        },
        audio: false,
      }
      
      const stream = await navigator.mediaDevices.getUserMedia(videoConstraints)
      
      // Start local stream session
      const { stream_session_id, video_id } = await videoService.startLocalStream('Local Camera')
      
      setLocalStreamSessionId(stream_session_id)
      setLocalVideoId(video_id)
      setLocalCameraStream(stream)
      setIsLocalCameraActive(true)
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream
      }
      
      // Setup canvas for frame capture
      if (canvasRef.current && videoRef.current) {
        const video = videoRef.current
        const canvas = canvasRef.current
        const ctx = canvas.getContext('2d')
        
        if (ctx) {
          // Wait for video to be ready
          const handleMetadataLoaded = () => {
            // Resize canvas to target dimensions (640x480 for bandwidth optimization)
            canvas.width = 640
            canvas.height = 480
            
            let isCapturing = true
            
            // Start frame capture loop
            const captureFrame = () => {
              const currentVideo = videoRef.current
              const currentCanvas = canvasRef.current
              
              if (!currentVideo || !currentCanvas || !ctx || !isCapturing || !isLocalCameraActive) {
                animationFrameRef.current = null
                return
              }
              
              const now = Date.now()
              const elapsed = now - lastFrameTimeRef.current
              
              // Capture at ~30 FPS (every ~33ms)
              if (elapsed >= 33) {
                try {
                  // Draw current video frame to canvas
                  ctx.drawImage(currentVideo, 0, 0, currentCanvas.width, currentCanvas.height)
                  
                  // Convert to blob
                  currentCanvas.toBlob(
                    (blob) => {
                      if (blob && sendFrame && stream_session_id) {
                        const metadata = {
                          timestamp: now / 1000, // seconds
                          width: currentCanvas.width,
                          height: currentCanvas.height,
                        }
                        
                        sendFrame(stream_session_id, blob, metadata)
                        
                        // Update stats (accumulate counts)
                        setStreamStats((prev) => ({
                          fps: prev.fps,
                          framesSent: prev.framesSent + 1,
                          bytesSent: prev.bytesSent + blob.size,
                        }))
                      }
                    },
                    'image/jpeg',
                    0.8 // 80% quality for bandwidth optimization
                  )
                  
                  lastFrameTimeRef.current = now
                } catch (err) {
                  console.error('Error capturing frame:', err)
                }
              }
              
              if (isCapturing) {
                animationFrameRef.current = requestAnimationFrame(captureFrame)
              }
            }
            
            // Start capture loop
            lastFrameTimeRef.current = Date.now()
            animationFrameRef.current = requestAnimationFrame(captureFrame)
            
            // Start stats tracking - update FPS every second
            statsIntervalRef.current = setInterval(() => {
              setStreamStats((prev) => {
                // FPS is frames sent in the last second (framesSent count)
                const fps = prev.framesSent
                const bytesSent = prev.bytesSent
                return { fps, framesSent: 0, bytesSent: 0 }
              })
            }, 1000) // Update every second
            
            // Store stop function
            ;(video as any)._stopCapture = () => {
              isCapturing = false
            }
          }
          
          if (video.readyState >= 2) {
            // Video already loaded
            handleMetadataLoaded()
          } else {
            video.onloadedmetadata = handleMetadataLoaded
          }
        }
      }
      
      toast.success('Local camera started')
      await fetchActiveStreams()
    } catch (error: any) {
      console.error('Failed to access local camera:', error)
      
      if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
        toast.error('Camera access denied. Please enable in browser settings.')
      } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
        toast.error('No camera found. Please connect a camera device.')
      } else {
        toast.error(`Failed to access local camera: ${error.message || 'Unknown error'}`)
      }
      
      // Cleanup on error
      if (localStreamSessionId) {
        try {
          await videoService.stopLocalStream(localStreamSessionId)
        } catch {
          // Ignore cleanup errors
        }
        setLocalStreamSessionId(null)
      }
    }
  }, [activeStreams.length, maxStreams, sendFrame, isLocalCameraActive, localCameraStream, localStreamSessionId])

  const handleStopLocalCamera = useCallback(async () => {
    // Stop animation frame loop
    if (animationFrameRef.current !== null) {
      cancelAnimationFrame(animationFrameRef.current)
      animationFrameRef.current = null
    }
    
    // Stop capture if video element has stop function
    if (videoRef.current && (videoRef.current as any)._stopCapture) {
      (videoRef.current as any)._stopCapture()
    }
    
    // Stop stats interval
    if (statsIntervalRef.current) {
      clearInterval(statsIntervalRef.current)
      statsIntervalRef.current = null
    }
    
    const sessionIdToStop = localStreamSessionId
    
    // Stop stream via WebSocket
    if (sessionIdToStop && stopLocalStreamSocket) {
      stopLocalStreamSocket(sessionIdToStop)
    }
    
    // Stop backend session
    if (sessionIdToStop) {
      try {
        await videoService.stopLocalStream(sessionIdToStop)
      } catch (error) {
        console.error('Error stopping local stream:', error)
      }
      setLocalStreamSessionId(null)
    }
    
    // Stop camera tracks
    if (localCameraStream) {
      localCameraStream.getTracks().forEach(track => track.stop())
      setLocalCameraStream(null)
    }
    
    setIsLocalCameraActive(false)
    setLocalVideoId(null)
    setStreamStats({ fps: 0, framesSent: 0, bytesSent: 0 })
    
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    
    toast.success('Local camera stopped')
    await fetchActiveStreams()
  }, [localCameraStream, localStreamSessionId, stopLocalStreamSocket, fetchActiveStreams])

  // Handle local stream WebSocket events
  useEffect(() => {
    if (!localStreamSocket) return

    const handleError = (data: { session_id: string; error: string; timestamp: string }) => {
      if (data.session_id === localStreamSessionId) {
        toast.error(`Stream error: ${data.error}`)
      }
    }

    const handleStreamStopped = (data: { session_id: string; timestamp: string }) => {
      if (data.session_id === localStreamSessionId) {
        console.log('Stream stopped by server')
      }
    }

    localStreamSocket.on('error', handleError)
    localStreamSocket.on('stream_stopped', handleStreamStopped)

    return () => {
      localStreamSocket.off('error', handleError)
      localStreamSocket.off('stream_stopped', handleStreamStopped)
    }
  }, [localStreamSocket, localStreamSessionId])

  // Handle WebSocket connection errors
  useEffect(() => {
    if (localStreamError && isLocalCameraActive) {
      toast.error(`Stream connection error: ${localStreamError}`)
    }
  }, [localStreamError, isLocalCameraActive])

  // Cleanup local camera stream on unmount
  useEffect(() => {
    return () => {
      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(animationFrameRef.current)
      }
      if (statsIntervalRef.current) {
        clearInterval(statsIntervalRef.current)
      }
      if (localCameraStream) {
        localCameraStream.getTracks().forEach(track => track.stop())
      }
    }
  }, [localCameraStream])

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      {/* Page Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center mb-2">
            <Eye className="h-8 w-8 text-primary-600 mr-2" />
            <h1 className="text-3xl font-bold text-gray-900">VigilentEye</h1>
          </div>
          <p className="text-gray-600">
            Upload videos or start live camera streaming for AI-powered surveillance
          </p>
        </div>
        {/* WebSocket Status Badge */}
        <div className="flex items-center space-x-2">
          <div
            className={`w-3 h-3 rounded-full ${
              isConnected ? 'bg-green-500' : 'bg-red-500'
            }`}
            title={isConnected ? 'WebSocket Connected' : 'WebSocket Disconnected'}
          />
          <span className="text-sm text-gray-600">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Two-Column Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mt-8">
        {/* Left Column: Upload Section */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center mb-4">
            <Upload className="h-6 w-6 text-primary-600 mr-2" />
            <h2 className="text-xl font-semibold text-gray-900">Upload Video</h2>
          </div>

          <UploadZone
            onFileSelect={handleFileSelect}
            accept="video/*"
            maxSizeMB={MAX_VIDEO_SIZE_MB}
            isUploading={isUploading}
            uploadProgress={uploadProgress}
            disabled={isUploading}
          />
        </div>

        {/* Right Column: Live Camera Section */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center mb-4">
            <Camera className="h-6 w-6 text-primary-600 mr-2" />
            <h2 className="text-xl font-semibold text-gray-900">Live Camera Stream</h2>
          </div>

          {/* Camera Type Tabs */}
          <div className="flex space-x-2 mb-4 border-b border-gray-200">
            <button
              className={`px-4 py-2 text-sm font-medium ${
                cameraMode === 'rtsp'
                  ? 'border-b-2 border-primary-600 text-primary-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              onClick={() => {
                setCameraMode('rtsp')
              }}
            >
              RTSP Stream
            </button>
            <button
              className={`px-4 py-2 text-sm font-medium ${
                cameraMode === 'local'
                  ? 'border-b-2 border-primary-600 text-primary-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              onClick={() => {
                setCameraMode('local')
              }}
            >
              Local Camera
            </button>
          </div>

          {cameraMode === 'rtsp' ? (
            /* RTSP Stream Section */
            <div className="space-y-4">
              {/* Stream URL Input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Stream URL <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  placeholder="rtsp://camera-ip:554/stream or http://..."
                  value={streamUrl}
                  onChange={(e) => setStreamUrl(e.target.value)}
                  disabled={isStreaming}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm disabled:bg-gray-100 disabled:cursor-not-allowed px-3 py-2 border"
                />
              </div>

              {/* Camera Name Input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Camera Name (Optional)
                </label>
                <input
                  type="text"
                  placeholder="Front Entrance"
                  value={cameraName}
                  onChange={(e) => setCameraName(e.target.value)}
                  disabled={isStreaming}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm disabled:bg-gray-100 disabled:cursor-not-allowed px-3 py-2 border"
                />
              </div>

              {/* Action Buttons */}
              {!isStreaming ? (
                <Button
                  onClick={handleStartStream}
                  disabled={!streamUrl.trim() || activeStreams.length >= maxStreams}
                  isLoading={isStartingStream}
                  fullWidth
                >
                  <Camera className="mr-2 h-5 w-5" />
                  Start Camera
                </Button>
              ) : (
                <Button
                  onClick={handleStopStream}
                  variant="danger"
                  isLoading={isStoppingStream}
                  fullWidth
                >
                  <StopCircle className="mr-2 h-5 w-5" />
                  Stop Camera
                </Button>
              )}

              {/* Stream Status Indicator */}
              <div className="flex items-center space-x-2 pt-2">
                {isStreaming ? (
                  <>
                    <div className="w-3 h-3 rounded-full bg-green-500" />
                    <span className="text-sm text-gray-700">🟢 Streaming</span>
                  </>
                ) : (
                  <>
                    <div className="w-3 h-3 rounded-full bg-gray-400" />
                    <span className="text-sm text-gray-700">⚫ Not streaming</span>
                  </>
                )}
              </div>

              {/* Max streams helper text */}
              {activeStreams.length >= maxStreams && (
                <p className="text-xs text-amber-600">
                  Maximum {maxStreams} concurrent streams reached
                </p>
              )}
            </div>
          ) : (
            /* Local Camera Section */
            <div className="space-y-4">
              {/* Video Preview */}
              <div className="relative bg-black rounded-lg overflow-hidden aspect-video">
                {isLocalCameraActive ? (
                  <>
                    <video
                      ref={videoRef}
                      autoPlay
                      playsInline
                      muted
                      className="w-full h-full object-contain"
                    />
                    {/* Overlay for streaming status */}
                    <div className="absolute top-2 left-2 flex items-center space-x-2 bg-black/70 rounded px-2 py-1">
                      {isLocalStreamConnected ? (
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-red-500" />
                      )}
                      <span className="text-xs text-white">
                        {isLocalStreamConnected ? 'Streaming to server' : 'Reconnecting...'}
                      </span>
                    </div>
                  </>
                ) : (
                  <div className="flex items-center justify-center h-full text-gray-400">
                    <Camera className="h-12 w-12" />
                  </div>
                )}
                <canvas ref={canvasRef} className="hidden" />
              </div>

              {/* Stream Health Indicators */}
              {isLocalCameraActive && (
                <div className="bg-gray-50 rounded-md p-3 space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Connection Status:</span>
                    <span className={`font-medium ${isLocalStreamConnected ? 'text-green-600' : 'text-red-600'}`}>
                      {isLocalStreamConnected ? 'Connected' : 'Disconnected'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Frame Rate:</span>
                    <span className="font-medium text-gray-900">{streamStats.fps.toFixed(1)} FPS</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Data Rate:</span>
                    <span className="font-medium text-gray-900">
                      {streamStats.bytesSent > 0 ? `${(streamStats.bytesSent / 1024).toFixed(1)} KB/s` : '0 KB/s'}
                    </span>
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              {!isLocalCameraActive ? (
                <Button
                  onClick={handleStartLocalCamera}
                  disabled={activeStreams.length >= maxStreams}
                  fullWidth
                >
                  <Camera className="mr-2 h-5 w-5" />
                  Start Local Camera
                </Button>
              ) : (
                <Button
                  onClick={handleStopLocalCamera}
                  variant="danger"
                  fullWidth
                >
                  <StopCircle className="mr-2 h-5 w-5" />
                  Stop Camera
                </Button>
              )}

              {/* Status Indicator */}
              <div className="flex items-center space-x-2 pt-2">
                {isLocalCameraActive ? (
                  <>
                    <div className={`w-3 h-3 rounded-full ${isLocalStreamConnected ? 'bg-green-500' : 'bg-yellow-500'}`} />
                    <span className="text-sm text-gray-700">
                      {isLocalStreamConnected ? '🟢 Local camera streaming' : '🟡 Local camera active (connecting...)'}
                    </span>
                  </>
                ) : (
                  <>
                    <div className="w-3 h-3 rounded-full bg-gray-400" />
                    <span className="text-sm text-gray-700">⚫ Local camera inactive</span>
                  </>
                )}
              </div>

              {/* Max streams helper text */}
              {activeStreams.length >= maxStreams && !isLocalCameraActive && (
                <p className="text-xs text-amber-600">
                  Maximum {maxStreams} concurrent streams reached
                </p>
              )}
            </div>
          )}

          {/* Active Streams List */}
          <div className="mt-6 pt-6 border-t border-gray-200">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">
              Active Streams ({activeStreams.length}/{maxStreams})
            </h3>

            {isLoadingStreams ? (
              <div className="space-y-2">
                {[1, 2].map((i) => (
                  <div
                    key={i}
                    className="animate-pulse bg-gray-200 h-16 rounded-md"
                  />
                ))}
              </div>
            ) : activeStreams.length === 0 ? (
              <p className="text-sm text-gray-500">No active streams</p>
            ) : (
              <div className="space-y-2">
                {activeStreams.map((stream) => (
                  <div
                    key={stream.camera_id}
                    className="bg-gray-50 rounded-md p-3 border border-gray-200"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900">
                          {stream.camera_name || 'Unnamed Camera'}
                        </p>
                        <p className="text-xs text-gray-500 mt-1 truncate">
                          {stream.stream_url}
                        </p>
                        <p className="text-xs text-gray-400 mt-1">
                          Started: {new Date(stream.started_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

