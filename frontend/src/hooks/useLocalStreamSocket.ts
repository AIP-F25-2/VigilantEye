import { useState, useEffect, useCallback } from 'react'
import { io, type Socket } from 'socket.io-client'
import { SOCKET_BASE_URL } from '@/utils/constants'

export interface LocalStreamSocketEvents {
  frame_ack: (data: { session_id: string; frame_id?: string; timestamp: string }) => void
  analysis_started: (data: { session_id: string; video_id: string; timestamp: string }) => void
  analysis_complete: (data: { session_id: string; video_id: string; result: string; timestamp: string }) => void
  error: (data: { session_id: string; error: string; timestamp: string }) => void
  stream_stopped: (data: { session_id: string; timestamp: string }) => void
}

export function useLocalStreamSocket(streamSessionId: string | null) {
  const [isConnected, setIsConnected] = useState(false)
  const [socket, setSocket] = useState<Socket | null>(null)
  const [connectionError, setConnectionError] = useState<string | null>(null)

  useEffect(() => {
    if (!streamSessionId) {
      return
    }

    const token = localStorage.getItem('access_token')
    if (!token) {
      setConnectionError('No authentication token found')
      return
    }

    const socketInstance = io(SOCKET_BASE_URL + '/local-stream', {
      auth: {
        token,
      },
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    })

    socketInstance.on('connect', () => {
      setIsConnected(true)
      setConnectionError(null)
      console.log('Local stream socket connected')
    })

    socketInstance.on('disconnect', () => {
      setIsConnected(false)
      console.log('Local stream socket disconnected')
    })

    socketInstance.on('connect_error', (error) => {
      console.error('Local stream socket connection error:', error)
      setIsConnected(false)
      setConnectionError(error.message || 'Connection failed')
    })

    setSocket(socketInstance)

    return () => {
      socketInstance.disconnect()
    }
  }, [streamSessionId])

  const sendFrame = useCallback(
    (
      sessionId: string,
      frameBlob: Blob,
      metadata: { timestamp: number; width: number; height: number }
    ) => {
      if (!socket || !isConnected) {
        console.warn('Socket not connected, cannot send frame')
        return false
      }

      // Convert blob to base64 for transmission
      const reader = new FileReader()
      reader.onloadend = () => {
        const base64data = reader.result as string
        // Remove data URL prefix if present
        const base64 = base64data.includes(',') ? base64data.split(',')[1] : base64data

        socket.emit('frame_data', {
          session_id: sessionId,
          frame: base64,
          timestamp: metadata.timestamp,
          width: metadata.width,
          height: metadata.height,
        })
      }
      reader.onerror = () => {
        console.error('Failed to read frame blob')
      }
      reader.readAsDataURL(frameBlob)
      return true
    },
    [socket, isConnected]
  )

  const stopStream = useCallback(
    (sessionId: string) => {
      if (!socket || !isConnected) {
        return false
      }

      socket.emit('stop_stream', {
        session_id: sessionId,
      })
      return true
    },
    [socket, isConnected]
  )

  return {
    socket,
    isConnected,
    connectionError,
    sendFrame,
    stopStream,
  }
}

