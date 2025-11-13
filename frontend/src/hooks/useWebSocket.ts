import { useState, useEffect } from 'react'
import { io, type Socket } from 'socket.io-client'
import { SOCKET_BASE_URL } from '@/utils/constants'

interface UseWebSocketOptions {
  namespace?: string
  auth?: boolean
}

export function useWebSocket(options: string | UseWebSocketOptions = '/analysis') {
  const namespace = typeof options === 'string' ? options : options.namespace || '/analysis'
  const useAuth = typeof options === 'object' ? options.auth !== false : false
  
  const [isConnected, setIsConnected] = useState(false)
  const [socket, setSocket] = useState<Socket | null>(null)

  useEffect(() => {
    const token = useAuth ? localStorage.getItem('access_token') : null
    const socketOptions: any = {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    }

    if (token && useAuth) {
      socketOptions.auth = {
        token,
      }
    }

    const socketInstance = io(SOCKET_BASE_URL + namespace, socketOptions)

    socketInstance.on('connect', () => {
      setIsConnected(true)
    })

    socketInstance.on('disconnect', () => {
      setIsConnected(false)
    })

    socketInstance.on('connect_error', (error) => {
      console.error('Socket connection error:', error)
      setIsConnected(false)
    })

    setSocket(socketInstance)

    return () => {
      socketInstance.disconnect()
    }
  }, [namespace, useAuth])

  return { socket, isConnected }
}

