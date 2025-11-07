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
  Trash2,
  FileSearch,
  Download,
} from 'lucide-react'
import Logo from '../components/Logo'
import { useAuthStore } from '../store/authStore'
import { videoAPI } from '../services/api'

const Dashboard = () => {
  const navigate = useNavigate()
  const { user, clearAuth } = useAuthStore()
  
  const [activeTab, setActiveTab] = useState('upload') // 'upload', 'camera', or 'videos'
  const [selectedFile, setSelectedFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [cameraActive, setCameraActive] = useState(false)
  const [recording, setRecording] = useState(false)
  const [videos, setVideos] = useState([])
  const [loadingVideos, setLoadingVideos] = useState(false)
  const [selectedVideo, setSelectedVideo] = useState(null)
  const [analyzingVideoId, setAnalyzingVideoId] = useState(null)
  const [deletingVideoId, setDeletingVideoId] = useState(null)
  const [playingVideoId, setPlayingVideoId] = useState(null)
  
  const videoRef = useRef(null)
  const fileInputRef = useRef(null)
  const mediaStreamRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const recordedChunksRef = useRef([])
  const streamVideoIdRef = useRef(null)
  const videoEventHandlersRef = useRef({})

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
        `Video ID: ${response.id}\n\n` +
        `Processing has started. Check "My Videos" tab to see results.`
      )
      setSelectedFile(null)
      setUploadProgress(0)
      // Switch to videos tab to see the uploaded video
      setActiveTab('videos')
      loadVideos()
    } catch (error) {
      console.error('Upload error:', error)
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to upload video'
      alert('Upload failed: ' + errorMsg)
    } finally {
      setUploading(false)
    }
  }

  const loadVideos = async () => {
    setLoadingVideos(true)
    try {
      const response = await videoAPI.getVideos()
      setVideos(response.videos || [])
    } catch (error) {
      console.error('Failed to load videos:', error)
      alert('Failed to load videos: ' + (error.response?.data?.detail || error.message))
    } finally {
      setLoadingVideos(false)
    }
  }

  const loadVideoDetails = async (videoId) => {
    try {
      const video = await videoAPI.getVideo(videoId)
      // Parse analysis results if available
      if (video.analysis_results) {
        try {
          video.parsedAnalysisResults = JSON.parse(video.analysis_results)
        } catch (e) {
          console.error('Failed to parse analysis results:', e)
          video.parsedAnalysisResults = null
        }
      }
      setSelectedVideo(video)
    } catch (error) {
      console.error('Failed to load video details:', error)
      alert('Failed to load video details: ' + (error.response?.data?.detail || error.message))
    }
  }

  const handleAnalyzeVideo = async (videoId, e) => {
    e.stopPropagation()
    if (!window.confirm('Start analysis for this video? This will extract frames and audio.')) {
      return
    }

    setAnalyzingVideoId(videoId)
    try {
      const response = await videoAPI.analyzeVideo(videoId)
      alert('Analysis started! The video will be processed in the background. Check back later for results.')
      // Refresh video list after a delay
      setTimeout(() => {
        loadVideos()
      }, 2000)
    } catch (error) {
      console.error('Failed to start analysis:', error)
      alert('Failed to start analysis: ' + (error.response?.data?.detail || error.message))
    } finally {
      setAnalyzingVideoId(null)
    }
  }

  const handleDeleteVideo = async (videoId, e) => {
    e.stopPropagation()
    if (!window.confirm('Are you sure you want to delete this video? This will permanently delete the video file and all analysis results.')) {
      return
    }

    setDeletingVideoId(videoId)
    try {
      await videoAPI.deleteVideo(videoId)
      alert('Video deleted successfully')
      loadVideos()
    } catch (error) {
      console.error('Failed to delete video:', error)
      alert('Failed to delete video: ' + (error.response?.data?.detail || error.message))
    } finally {
      setDeletingVideoId(null)
    }
  }

  const handlePlayVideo = async (videoId, e) => {
    e.stopPropagation()
    setPlayingVideoId(videoId)
    try {
      const video = await videoAPI.getVideo(videoId)
      setSelectedVideo({ ...video, playMode: true })
    } catch (error) {
      console.error('Failed to load video for playback:', error)
      alert('Failed to load video: ' + (error.response?.data?.detail || error.message))
      setPlayingVideoId(null)
    }
  }

  const startCamera = async () => {
    try {
      // Check if getUserMedia is available
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        const error = new Error('Camera access is not supported in this browser.')
        alert(error.message)
        throw error
      }

      // Wait a bit to ensure video element is in DOM
      let retries = 0
      while (!videoRef.current && retries < 10) {
        await new Promise(resolve => setTimeout(resolve, 50))
        retries++
      }

      if (!videoRef.current) {
        console.error('Video element not found after waiting')
        throw new Error('Video element not available')
      }

      const video = videoRef.current
      console.log('Video element found:', video)

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { 
          width: { ideal: 1280 }, 
          height: { ideal: 720 },
          facingMode: 'user' // Use front-facing camera by default
        },
        audio: false,
      })
      
      console.log('Stream obtained:', stream)
      console.log('Video tracks:', stream.getVideoTracks())
      console.log('Track settings:', stream.getVideoTracks()[0]?.getSettings())
      
      mediaStreamRef.current = stream
      
      // Clean up any existing event listeners first
      if (videoEventHandlersRef.current && Object.keys(videoEventHandlersRef.current).length > 0) {
        Object.entries(videoEventHandlersRef.current).forEach(([event, handler]) => {
          video.removeEventListener(event, handler)
        })
      }
      videoEventHandlersRef.current = {}
      
      // Set up event listeners
      const handleLoadedMetadata = () => {
        console.log('Video metadata loaded, dimensions:', video.videoWidth, 'x', video.videoHeight)
        video.play().catch((err) => {
          console.error('Error in play promise from loadedmetadata:', err)
        })
      }
      
      const handleLoadedData = () => {
        console.log('Video data loaded')
      }
      
      const handleCanPlay = () => {
        console.log('Video can play')
        setCameraActive(true)
      }
      
      const handleCanPlayThrough = () => {
        console.log('Video can play through')
      }
      
      const handlePlay = () => {
        console.log('Video is playing, currentTime:', video.currentTime)
        setCameraActive(true)
      }
      
      const handlePlaying = () => {
        console.log('Video is actually playing')
      }
      
      const handleError = (e) => {
        console.error('Video error event:', e)
        console.error('Video error code:', video.error?.code)
        console.error('Video error message:', video.error?.message)
      }
      
      // Store handlers for cleanup
      videoEventHandlersRef.current = {
        'loadedmetadata': handleLoadedMetadata,
        'loadeddata': handleLoadedData,
        'canplay': handleCanPlay,
        'canplaythrough': handleCanPlayThrough,
        'play': handlePlay,
        'playing': handlePlaying,
        'error': handleError
      }
      
      // Add event listeners
      Object.entries(videoEventHandlersRef.current).forEach(([event, handler]) => {
        video.addEventListener(event, handler)
      })
      
      // Set the stream
      console.log('Setting srcObject on video element')
      video.srcObject = stream
      
      // Force video to be visible
      video.style.display = 'block'
      video.style.visibility = 'visible'
      
      // Try to play immediately
      try {
        console.log('Attempting to play video...')
        await video.play()
        console.log('Video play() succeeded immediately')
        setCameraActive(true)
      } catch (playError) {
        console.warn('Initial play() failed, waiting for events:', playError)
        // The loadedmetadata/canplay events will trigger play() and setCameraActive
      }
      
    } catch (err) {
      console.error('Error accessing camera:', err)
      let errorMessage = 'Could not access camera. '
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        errorMessage += 'Please allow camera access in your browser settings.'
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        errorMessage += 'No camera found. Please connect a camera device.'
      } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
        errorMessage += 'Camera is already in use by another application.'
      } else {
        errorMessage += err.message || 'Please check permissions and try again.'
      }
      alert(errorMessage)
      throw err
    }
  }

  const stopCamera = () => {
    console.log('Stopping camera...')
    
    // Stop recording if active
    if (recording && mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      console.log('Stopping recording...')
      try {
        mediaRecorderRef.current.stop()
        mediaRecorderRef.current = null
      } catch (err) {
        console.error('Error stopping recorder:', err)
      }
    }
    
    // Stop all media stream tracks
    if (mediaStreamRef.current) {
      console.log('Stopping media stream tracks...')
      mediaStreamRef.current.getTracks().forEach((track) => {
        track.stop()
        console.log('Stopped track:', track.kind, track.label, 'readyState:', track.readyState)
      })
      mediaStreamRef.current = null
    }
    
    // Clean up video element
    if (videoRef.current) {
      const video = videoRef.current
      console.log('Cleaning up video element...')
      
      // Pause video
      try {
        video.pause()
      } catch (err) {
        console.error('Error pausing video:', err)
      }
      
      // Remove event listeners
      if (videoEventHandlersRef.current) {
        Object.entries(videoEventHandlersRef.current).forEach(([event, handler]) => {
          try {
            video.removeEventListener(event, handler)
          } catch (err) {
            console.error(`Error removing ${event} listener:`, err)
          }
        })
        videoEventHandlersRef.current = {}
      }
      
      // Clear srcObject
      try {
        video.srcObject = null
      } catch (err) {
        console.error('Error clearing srcObject:', err)
      }
      
      // Clear video source
      try {
        video.load() // Reset video element
      } catch (err) {
        console.error('Error loading video:', err)
      }
    }
    
    // Reset state
    setCameraActive(false)
    setRecording(false)
    streamVideoIdRef.current = null
    recordedChunksRef.current = []
    
    console.log('Camera stopped successfully')
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

  // Auto-start camera when camera tab is selected
  useEffect(() => {
    if (activeTab === 'camera' && !cameraActive && !mediaStreamRef.current) {
      // Small delay to ensure video element is mounted
      const timer = setTimeout(() => {
        if (videoRef.current) {
          startCamera().catch((error) => {
            console.error('Failed to auto-start camera:', error)
            // Error is already handled in startCamera function
          })
        } else {
          console.error('Video element not available for camera start')
        }
      }, 100)
      
      return () => clearTimeout(timer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab])

  // Ensure video plays when stream is set
  useEffect(() => {
    if (videoRef.current && mediaStreamRef.current && cameraActive) {
      const video = videoRef.current
      const playPromise = video.play()
      
      if (playPromise !== undefined) {
        playPromise
          .then(() => {
            console.log('Video is playing')
          })
          .catch((error) => {
            console.error('Error playing video:', error)
          })
      }
    }
  }, [cameraActive])

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
            onClick={() => {
              setActiveTab('camera')
              // Auto-start camera when switching to camera tab
              if (!cameraActive) {
                startCamera()
              }
            }}
            className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-all ${
              activeTab === 'camera'
                ? 'bg-primary-600 text-white'
                : 'bg-dark-800 text-gray-400 hover:bg-dark-700'
            }`}
          >
            <Camera className="w-5 h-5" />
            Live Camera
          </button>
          <button
            onClick={() => {
              setActiveTab('videos')
              stopCamera()
              loadVideos()
            }}
            className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-all ${
              activeTab === 'videos'
                ? 'bg-primary-600 text-white'
                : 'bg-dark-800 text-gray-400 hover:bg-dark-700'
            }`}
          >
            <Video className="w-5 h-5" />
            My Videos
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
          ) : activeTab === 'camera' ? (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold flex items-center gap-2">
                  <Camera className="w-6 h-6 text-primary-500" />
                  Live Camera Feed
                </h2>
              </div>

              {/* Camera View */}
              <div className="relative bg-black rounded-lg overflow-hidden aspect-video min-h-[400px]">
                {/* Always render video element, but hide when not active */}
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className={`w-full h-full object-cover ${cameraActive ? 'block' : 'hidden'}`}
                  style={{ display: cameraActive ? 'block' : 'none' }}
                />
                
                {/* Loading state */}
                {!cameraActive && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="text-center">
                      <Loader2 className="w-16 h-16 mx-auto mb-4 text-gray-600 animate-spin" />
                      <p className="text-gray-500 mb-4">Starting camera...</p>
                    </div>
                  </div>
                )}
                
                {/* Recording indicator */}
                {recording && cameraActive && (
                  <div className="absolute top-4 left-4 flex items-center gap-2 bg-red-500/90 text-white px-3 py-1 rounded-full text-sm font-medium z-10">
                    <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
                    Recording
                  </div>
                )}
                
                {/* Scanning Effect */}
                {cameraActive && <div className="scan-line"></div>}
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
                    className="btn-secondary flex items-center gap-2"
                  >
                    <X className="w-5 h-5" />
                    Stop Camera
                  </button>
                </div>
              )}
            </div>
          ) : activeTab === 'videos' ? (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold flex items-center gap-2">
                  <Video className="w-6 h-6 text-primary-500" />
                  My Videos
                </h2>
                <button
                  onClick={loadVideos}
                  className="btn-secondary flex items-center gap-2"
                  disabled={loadingVideos}
                >
                  <Loader2 className={`w-4 h-4 ${loadingVideos ? 'animate-spin' : ''}`} />
                  Refresh
                </button>
              </div>

              {loadingVideos ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
                </div>
              ) : videos.length === 0 ? (
                <div className="text-center py-12">
                  <Video className="w-16 h-16 mx-auto mb-4 text-gray-600" />
                  <p className="text-gray-500 mb-4">No videos uploaded yet</p>
                  <button
                    onClick={() => setActiveTab('upload')}
                    className="btn-primary"
                  >
                    Upload Your First Video
                  </button>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-800">
                        <th className="text-left py-3 px-4 text-sm font-semibold text-gray-400">Filename</th>
                        <th className="text-left py-3 px-4 text-sm font-semibold text-gray-400">Status</th>
                        <th className="text-left py-3 px-4 text-sm font-semibold text-gray-400">Size</th>
                        <th className="text-left py-3 px-4 text-sm font-semibold text-gray-400">Duration</th>
                        <th className="text-left py-3 px-4 text-sm font-semibold text-gray-400">Created</th>
                        <th className="text-left py-3 px-4 text-sm font-semibold text-gray-400">Analysis</th>
                        <th className="text-right py-3 px-4 text-sm font-semibold text-gray-400">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {videos.map((video) => {
                        let analysisResults = null
                        let isAnalyzed = false
                        try {
                          if (video.analysis_results) {
                            analysisResults = JSON.parse(video.analysis_results)
                            isAnalyzed = analysisResults && analysisResults.status === 'completed'
                          }
                        } catch (e) {
                          console.error('Failed to parse analysis results:', e)
                        }
                        
                        const statusColors = {
                          'UPLOADED': 'bg-blue-500/20 text-blue-400',
                          'PROCESSING': 'bg-yellow-500/20 text-yellow-400',
                          'COMPLETED': 'bg-green-500/20 text-green-400',
                          'FAILED': 'bg-red-500/20 text-red-400',
                          'STREAMING': 'bg-purple-500/20 text-purple-400',
                        }
                        
                        const formatDate = (dateString) => {
                          if (!dateString) return 'N/A'
                          const date = new Date(dateString)
                          return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                        }
                        
                        return (
                          <tr 
                            key={video.id} 
                            className="border-b border-gray-800 hover:bg-dark-800/50 transition-colors"
                          >
                            <td className="py-4 px-4">
                              <div className="flex items-center gap-2">
                                <Video className="w-4 h-4 text-gray-500" />
                                <span className="text-gray-200 font-medium">{video.original_filename}</span>
                              </div>
                            </td>
                            <td className="py-4 px-4">
                              <span className={`text-xs px-2 py-1 rounded-full ${statusColors[video.status] || 'bg-gray-500/20 text-gray-400'}`}>
                                {video.status}
                              </span>
                            </td>
                            <td className="py-4 px-4 text-gray-400 text-sm">
                              {(video.file_size / 1024 / 1024).toFixed(2)} MB
                            </td>
                            <td className="py-4 px-4 text-gray-400 text-sm">
                              {video.duration ? `${video.duration.toFixed(1)}s` : 'N/A'}
                            </td>
                            <td className="py-4 px-4 text-gray-400 text-sm">
                              {formatDate(video.created_at)}
                            </td>
                            <td className="py-4 px-4">
                              {isAnalyzed ? (
                                <span className="text-green-400 text-sm">✓ Analyzed</span>
                              ) : video.status === 'PROCESSING' ? (
                                <span className="text-yellow-400 text-sm">Processing...</span>
                              ) : (
                                <span className="text-gray-500 text-sm">Not analyzed</span>
                              )}
                            </td>
                            <td className="py-4 px-4">
                              <div className="flex items-center justify-end gap-2">
                                <button
                                  onClick={(e) => handlePlayVideo(video.id, e)}
                                  className="p-2 hover:bg-primary-500/20 rounded-lg transition-colors"
                                  title="Play video"
                                  disabled={playingVideoId === video.id}
                                >
                                  {playingVideoId === video.id ? (
                                    <Loader2 className="w-4 h-4 text-primary-500 animate-spin" />
                                  ) : (
                                    <Play className="w-4 h-4 text-primary-500" />
                                  )}
                                </button>
                                <button
                                  onClick={(e) => handleAnalyzeVideo(video.id, e)}
                                  className="p-2 hover:bg-green-500/20 rounded-lg transition-colors"
                                  title="Analyze video"
                                  disabled={analyzingVideoId === video.id || video.status === 'PROCESSING'}
                                >
                                  {analyzingVideoId === video.id ? (
                                    <Loader2 className="w-4 h-4 text-green-500 animate-spin" />
                                  ) : (
                                    <FileSearch className="w-4 h-4 text-green-500" />
                                  )}
                                </button>
                                <button
                                  onClick={(e) => handleDeleteVideo(video.id, e)}
                                  className="p-2 hover:bg-red-500/20 rounded-lg transition-colors"
                                  title="Delete video"
                                  disabled={deletingVideoId === video.id}
                                >
                                  {deletingVideoId === video.id ? (
                                    <Loader2 className="w-4 h-4 text-red-500 animate-spin" />
                                  ) : (
                                    <Trash2 className="w-4 h-4 text-red-500" />
                                  )}
                                </button>
                              </div>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Video Details/Playback Modal */}
              {selectedVideo && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => {
                  setSelectedVideo(null)
                  setPlayingVideoId(null)
                }}>
                  <div className="bg-dark-900 rounded-xl max-w-6xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
                    <div className="p-6 border-b border-gray-800 flex items-center justify-between">
                      <h3 className="text-xl font-semibold">{selectedVideo.original_filename}</h3>
                      <button
                        onClick={() => {
                          setSelectedVideo(null)
                          setPlayingVideoId(null)
                        }}
                        className="p-2 hover:bg-dark-800 rounded-lg"
                      >
                        <X className="w-5 h-5" />
                      </button>
                    </div>
                    <div className="p-6 space-y-6">
                      {/* Video Player */}
                      {selectedVideo.playMode ? (
                        <div className="space-y-4">
                          <div className="relative bg-black rounded-lg overflow-hidden aspect-video">
                            <video
                              src={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/video/${selectedVideo.id}/download`}
                              controls
                              className="w-full h-full"
                              autoPlay
                            >
                              Your browser does not support video playback.
                            </video>
                          </div>
                          <div className="flex gap-4">
                            <button
                              onClick={async () => {
                                try {
                                  const blob = await videoAPI.downloadVideo(selectedVideo.id)
                                  const url = window.URL.createObjectURL(blob)
                                  const a = document.createElement('a')
                                  a.href = url
                                  a.download = selectedVideo.original_filename
                                  document.body.appendChild(a)
                                  a.click()
                                  window.URL.revokeObjectURL(url)
                                  document.body.removeChild(a)
                                } catch (error) {
                                  alert('Failed to download video: ' + (error.response?.data?.detail || error.message))
                                }
                              }}
                              className="btn-secondary flex items-center gap-2"
                            >
                              <Download className="w-4 h-4" />
                              Download Video
                            </button>
                          </div>
                        </div>
                      ) : null}

                      {/* Video Metadata */}
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <span className="text-gray-400 text-sm">Status:</span>
                          <p className="text-gray-200">{selectedVideo.status}</p>
                        </div>
                        <div>
                          <span className="text-gray-400 text-sm">File Size:</span>
                          <p className="text-gray-200">{(selectedVideo.file_size / 1024 / 1024).toFixed(2)} MB</p>
                        </div>
                        {selectedVideo.duration && (
                          <div>
                            <span className="text-gray-400 text-sm">Duration:</span>
                            <p className="text-gray-200">{selectedVideo.duration.toFixed(1)}s</p>
                          </div>
                        )}
                        {selectedVideo.width && selectedVideo.height && (
                          <div>
                            <span className="text-gray-400 text-sm">Resolution:</span>
                            <p className="text-gray-200">{selectedVideo.width}x{selectedVideo.height}</p>
                          </div>
                        )}
                        {selectedVideo.fps && (
                          <div>
                            <span className="text-gray-400 text-sm">FPS:</span>
                            <p className="text-gray-200">{selectedVideo.fps.toFixed(2)}</p>
                          </div>
                        )}
                        <div>
                          <span className="text-gray-400 text-sm">Created:</span>
                          <p className="text-gray-200">
                            {selectedVideo.created_at ? new Date(selectedVideo.created_at).toLocaleString() : 'N/A'}
                          </p>
                        </div>
                      </div>

                      {/* Analysis Results */}
                      {selectedVideo.parsedAnalysisResults ? (
                        <div className="border-t border-gray-800 pt-6">
                          <h4 className="text-lg font-semibold mb-4">Analysis Results</h4>
                          <div className="space-y-4">
                            {selectedVideo.parsedAnalysisResults.frames && (
                              <div className="bg-dark-800 p-4 rounded-lg">
                                <h5 className="font-semibold mb-2">Frame Extraction</h5>
                                <div className="grid grid-cols-2 gap-2 text-sm">
                                  <div>
                                    <span className="text-gray-400">Total Frames:</span>
                                    <span className="ml-2 text-gray-200">
                                      {selectedVideo.parsedAnalysisResults.frames.total_frames_extracted || 0}
                                    </span>
                                  </div>
                                  <div>
                                    <span className="text-gray-400">Interval:</span>
                                    <span className="ml-2 text-gray-200">
                                      {selectedVideo.parsedAnalysisResults.frames.extraction_interval_ms || 0}ms
                                    </span>
                                  </div>
                                  <div>
                                    <span className="text-gray-400">Resolution:</span>
                                    <span className="ml-2 text-gray-200">
                                      {selectedVideo.parsedAnalysisResults.frames.video_resolution || 'N/A'}
                                    </span>
                                  </div>
                                  <div>
                                    <span className="text-gray-400">FPS:</span>
                                    <span className="ml-2 text-gray-200">
                                      {selectedVideo.parsedAnalysisResults.frames.video_fps || 'N/A'}
                                    </span>
                                  </div>
                                </div>
                              </div>
                            )}
                            {selectedVideo.parsedAnalysisResults.audio && selectedVideo.parsedAnalysisResults.audio.has_audio && (
                              <div className="bg-dark-800 p-4 rounded-lg">
                                <h5 className="font-semibold mb-2">Audio Extraction</h5>
                                <div className="grid grid-cols-2 gap-2 text-sm">
                                  <div>
                                    <span className="text-gray-400">Duration:</span>
                                    <span className="ml-2 text-gray-200">
                                      {selectedVideo.parsedAnalysisResults.audio.duration_sec?.toFixed(2) || 'N/A'}s
                                    </span>
                                  </div>
                                  <div>
                                    <span className="text-gray-400">Sample Rate:</span>
                                    <span className="ml-2 text-gray-200">
                                      {selectedVideo.parsedAnalysisResults.audio.sample_rate || 'N/A'} Hz
                                    </span>
                                  </div>
                                  <div>
                                    <span className="text-gray-400">Channels:</span>
                                    <span className="ml-2 text-gray-200">
                                      {selectedVideo.parsedAnalysisResults.audio.channels || 'N/A'}
                                    </span>
                                  </div>
                                  <div>
                                    <span className="text-gray-400">File Size:</span>
                                    <span className="ml-2 text-gray-200">
                                      {selectedVideo.parsedAnalysisResults.audio.file_size_bytes 
                                        ? (selectedVideo.parsedAnalysisResults.audio.file_size_bytes / 1024 / 1024).toFixed(2) + ' MB'
                                        : 'N/A'}
                                    </span>
                                  </div>
                                </div>
                              </div>
                            )}
                            {selectedVideo.parsedAnalysisResults.processing_time_sec && (
                              <div className="text-sm text-gray-400">
                                Processing completed in {selectedVideo.parsedAnalysisResults.processing_time_sec.toFixed(2)} seconds
                              </div>
                            )}
                          </div>
                          <details className="mt-4">
                            <summary className="cursor-pointer text-gray-400 hover:text-gray-200 text-sm">
                              View Raw JSON
                            </summary>
                            <pre className="bg-dark-800 p-4 rounded-lg overflow-x-auto text-xs mt-2">
                              {JSON.stringify(selectedVideo.parsedAnalysisResults, null, 2)}
                            </pre>
                          </details>
                        </div>
                      ) : selectedVideo.analysis_results ? (
                        <div className="border-t border-gray-800 pt-6">
                          <h4 className="text-lg font-semibold mb-4">Analysis Results</h4>
                          <p className="text-red-400">Error parsing analysis results</p>
                        </div>
                      ) : (
                        <div className="border-t border-gray-800 pt-6">
                          <p className="text-gray-400">No analysis results available. Click the Analyze button to process this video.</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : null}
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
