import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  LogOut,
  Upload,
  Video,
  Camera,
  X,
  Play,
  Pause,
  User,
  Shield,
  Loader2,
  Ticket,
} from 'lucide-react'
import Logo from '../components/Logo'
import { useAuthStore } from '../store/authStore'
import { videoAPI } from '../services/api'

const Dashboard = () => {
  const navigate = useNavigate()
  const { user, clearAuth } = useAuthStore()
  
  const [activeTab, setActiveTab] = useState('upload') // 'upload' or 'camera'
  const [selectedFile, setSelectedFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [cameraActive, setCameraActive] = useState(false)
  const [recording, setRecording] = useState(false)
  
  const videoRef = useRef(null)
  const fileInputRef = useRef(null)
  const mediaStreamRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const recordedChunksRef = useRef([])
  const streamVideoIdRef = useRef(null)

  const handleLogout = () => {
    clearAuth()
    navigate('/login')
  }

  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    if (file && file.type.startsWith('video/')) {
      setSelectedFile(file)
    } else {
      alert('Please select a valid video file')
    }
  }

  const handleUpload = async () => {
    if (!selectedFile) return

    setUploading(true)
    setUploadProgress(0)

    try {
      const response = await videoAPI.uploadVideo(selectedFile, (progress) => {
        setUploadProgress(progress)
      })

      console.log('Upload response:', response)
      alert(
        `Video uploaded successfully!\n\n` +
        `File: ${response.original_filename}\n` +
        `Size: ${(response.file_size / 1024 / 1024).toFixed(2)} MB\n` +
        `Status: ${response.status}\n\n` +
        `Video ID: ${response.id}`
      )
      setSelectedFile(null)
      setUploadProgress(0)
    } catch (error) {
      console.error('Upload error:', error)
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to upload video'
      alert('Upload failed: ' + errorMsg)
    } finally {
      setUploading(false)
    }
  }

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 1280, height: 720 },
        audio: false,
      })
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        mediaStreamRef.current = stream
        setCameraActive(true)
      }
    } catch (err) {
      console.error('Error accessing camera:', err)
      alert('Could not access camera. Please check permissions.')
    }
  }

  const stopCamera = () => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop())
      mediaStreamRef.current = null
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    setCameraActive(false)
    setRecording(false)
  }

  const toggleRecording = async () => {
    if (!recording) {
      // Start recording
      try {
        // Start stream on backend
        const response = await videoAPI.startStream({
          device: 'webcam',
          timestamp: new Date().toISOString(),
        })
        
        streamVideoIdRef.current = response.id
        recordedChunksRef.current = []

        // Create MediaRecorder
        const options = { mimeType: 'video/webm;codecs=vp9' }
        if (!MediaRecorder.isTypeSupported(options.mimeType)) {
          options.mimeType = 'video/webm'
        }

        const mediaRecorder = new MediaRecorder(mediaStreamRef.current, options)
        mediaRecorderRef.current = mediaRecorder

        mediaRecorder.ondataavailable = async (event) => {
          if (event.data && event.data.size > 0) {
            recordedChunksRef.current.push(event.data)
            
            // Upload chunk to backend
            try {
              await videoAPI.uploadChunk(streamVideoIdRef.current, event.data)
              console.log('Chunk uploaded:', event.data.size, 'bytes')
            } catch (error) {
              console.error('Failed to upload chunk:', error)
            }
          }
        }

        mediaRecorder.start(1000) // Collect data every 1 second
        setRecording(true)
        console.log('Recording started, video ID:', response.id)
      } catch (error) {
        console.error('Failed to start recording:', error)
        alert('Failed to start recording: ' + (error.response?.data?.detail || error.message))
      }
    } else {
      // Stop recording
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop()
        
        // Wait a bit for final chunks
        setTimeout(async () => {
          try {
            // Stop stream on backend
            const response = await videoAPI.stopStream(streamVideoIdRef.current)
            console.log('Recording stopped:', response)
            alert(`Recording saved successfully! File size: ${(response.file_size / 1024 / 1024).toFixed(2)} MB`)
            
            recordedChunksRef.current = []
            streamVideoIdRef.current = null
          } catch (error) {
            console.error('Failed to stop stream:', error)
            alert('Failed to save recording: ' + (error.response?.data?.detail || error.message))
          }
        }, 1000)
      }
      setRecording(false)
    }
  }

  useEffect(() => {
    return () => {
      // Cleanup camera on unmount
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((track) => track.stop())
      }
    }
  }, [])

  return (
    <div className="min-h-screen bg-dark-950 grid-bg">
      {/* Header */}
      <header className="border-b border-gray-800 bg-dark-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <Logo size="md" />
            
            <div className="flex items-center gap-6">
              {/* Navigation */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => navigate('/dashboard')}
                  className="px-4 py-2 bg-primary-600 text-white rounded-lg"
                >
                  Dashboard
                </button>
                <button
                  onClick={() => navigate('/tickets')}
                  className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
                >
                  Tickets
                </button>
              </div>

              {/* User Info */}
              <div className="flex items-center gap-3 px-4 py-2 bg-dark-800 rounded-lg border border-gray-700">
                <div className="w-8 h-8 bg-primary-500/20 rounded-full flex items-center justify-center">
                  {user?.role === 'ADMIN' ? (
                    <Shield className="w-4 h-4 text-primary-500" />
                  ) : (
                    <User className="w-4 h-4 text-primary-500" />
                  )}
                </div>
                <div className="text-sm">
                  <div className="font-medium text-gray-200">{user?.username}</div>
                  <div className="text-xs text-gray-500">{user?.role}</div>
                </div>
              </div>

              {/* Logout Button */}
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg transition-colors border border-red-500/30"
              >
                <LogOut className="w-4 h-4" />
                <span className="text-sm font-medium">Logout</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Welcome Message */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">
            Welcome back, <span className="text-primary-500">{user?.full_name || user?.username}</span>
          </h1>
          <p className="text-gray-400">
            Start analyzing videos with AI-powered intelligence
          </p>
        </div>

        {/* Tabs */}
        <div className="flex gap-4 mb-6">
          <button
            onClick={() => {
              setActiveTab('upload')
              stopCamera()
            }}
            className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-all ${
              activeTab === 'upload'
                ? 'bg-primary-600 text-white'
                : 'bg-dark-800 text-gray-400 hover:bg-dark-700'
            }`}
          >
            <Upload className="w-5 h-5" />
            Upload Video
          </button>
          <button
            onClick={() => setActiveTab('camera')}
            className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-all ${
              activeTab === 'camera'
                ? 'bg-primary-600 text-white'
                : 'bg-dark-800 text-gray-400 hover:bg-dark-700'
            }`}
          >
            <Camera className="w-5 h-5" />
            Live Camera
          </button>
        </div>

        {/* Content Area */}
        <div className="card-glass">
          {activeTab === 'upload' ? (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold flex items-center gap-2">
                  <Video className="w-6 h-6 text-primary-500" />
                  Upload Video for Analysis
                </h2>
              </div>

              {/* Upload Area */}
              <div
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-gray-700 rounded-lg p-12 text-center cursor-pointer hover:border-primary-500 transition-colors relative overflow-hidden group"
              >
                <div className="relative z-10">
                  <Upload className="w-16 h-16 mx-auto mb-4 text-gray-500 group-hover:text-primary-500 transition-colors" />
                  <p className="text-lg font-medium text-gray-300 mb-2">
                    Click to upload or drag and drop
                  </p>
                  <p className="text-sm text-gray-500">
                    MP4, AVI, MOV up to 500MB
                  </p>
                </div>
                <div className="absolute inset-0 bg-primary-500/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
              </div>

              <input
                ref={fileInputRef}
                type="file"
                accept="video/*"
                onChange={handleFileSelect}
                className="hidden"
              />

              {/* Selected File */}
              {selectedFile && (
                <div className="bg-dark-800 rounded-lg p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-primary-500/20 rounded-lg flex items-center justify-center">
                      <Video className="w-6 h-6 text-primary-500" />
                    </div>
                    <div>
                      <div className="font-medium text-gray-200">{selectedFile.name}</div>
                      <div className="text-sm text-gray-500">
                        {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => setSelectedFile(null)}
                    className="p-2 hover:bg-dark-700 rounded-lg transition-colors"
                  >
                    <X className="w-5 h-5 text-gray-400" />
                  </button>
                </div>
              )}

              {/* Upload Progress */}
              {uploading && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-400">Uploading...</span>
                    <span className="text-primary-500 font-medium">{uploadProgress}%</span>
                  </div>
                  <div className="h-2 bg-dark-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary-500 transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    ></div>
                  </div>
                </div>
              )}

              {/* Upload Button */}
              <button
                onClick={handleUpload}
                disabled={!selectedFile || uploading}
                className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {uploading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <Upload className="w-5 h-5" />
                    Upload and Analyze
                  </>
                )}
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold flex items-center gap-2">
                  <Camera className="w-6 h-6 text-primary-500" />
                  Live Camera Feed
                </h2>
              </div>

              {/* Camera View */}
              <div className="relative bg-black rounded-lg overflow-hidden aspect-video">
                {cameraActive ? (
                  <>
                    <video
                      ref={videoRef}
                      autoPlay
                      playsInline
                      className="w-full h-full object-cover"
                    />
                    {recording && (
                      <div className="absolute top-4 left-4 flex items-center gap-2 bg-red-500/90 text-white px-3 py-1 rounded-full text-sm font-medium">
                        <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
                        Recording
                      </div>
                    )}
                    {/* Scanning Effect */}
                    <div className="scan-line"></div>
                  </>
                ) : (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="text-center">
                      <Camera className="w-16 h-16 mx-auto mb-4 text-gray-600" />
                      <p className="text-gray-500 mb-4">Camera is not active</p>
                      <button onClick={startCamera} className="btn-primary">
                        Start Camera
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Camera Controls */}
              {cameraActive && (
                <div className="flex gap-4">
                  <button
                    onClick={toggleRecording}
                    className={`flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-lg font-medium transition-all ${
                      recording
                        ? 'bg-red-600 hover:bg-red-700 text-white'
                        : 'bg-primary-600 hover:bg-primary-700 text-white'
                    }`}
                  >
                    {recording ? (
                      <>
                        <Pause className="w-5 h-5" />
                        Stop Recording
                      </>
                    ) : (
                      <>
                        <Play className="w-5 h-5" />
                        Start Recording
                      </>
                    )}
                  </button>
                  <button
                    onClick={stopCamera}
                    className="btn-secondary"
                  >
                    <X className="w-5 h-5" />
                    Stop Camera
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Info Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
          <div className="card">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-primary-500/20 rounded-lg flex items-center justify-center">
                <Video className="w-5 h-5 text-primary-500" />
              </div>
              <h3 className="font-semibold">Video Analysis</h3>
            </div>
            <p className="text-sm text-gray-400">
              AI-powered object detection, tracking, and behavior analysis
            </p>
          </div>

          <div className="card">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-green-500/20 rounded-lg flex items-center justify-center">
                <Camera className="w-5 h-5 text-green-500" />
              </div>
              <h3 className="font-semibold">Real-time Monitoring</h3>
            </div>
            <p className="text-sm text-gray-400">
              Live camera feed with instant AI analysis and alerts
            </p>
          </div>

          <div className="card">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-purple-500/20 rounded-lg flex items-center justify-center">
                <Shield className="w-5 h-5 text-purple-500" />
              </div>
              <h3 className="font-semibold">Secure & Private</h3>
            </div>
            <p className="text-sm text-gray-400">
              Your data is encrypted and processed with enterprise-grade security
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}

export default Dashboard
