import { useState, useEffect, useCallback, useRef } from 'react'

// Build WebSocket URL from API URL or use localhost
const getWsUrl = () => {
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
  // Convert http(s) to ws(s)
  return apiUrl.replace(/^http/, 'ws')
}

const WS_BASE = getWsUrl()

export function useWebSocket(conversationId, onTitleUpdate) {
  const [isConnected, setIsConnected] = useState(false)
  const [messages, setMessages] = useState([])
  const [isTyping, setIsTyping] = useState(false)
  const [currentResponse, setCurrentResponse] = useState('')
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)

  const connect = useCallback(() => {
    if (!conversationId) return

    const ws = new WebSocket(`${WS_BASE}/chat/ws/${conversationId}`)
    wsRef.current = ws

    ws.onopen = () => {
      setIsConnected(true)
      console.log('WebSocket connected')
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)

      switch (data.type) {
        case 'chunk':
          setIsTyping(true)
          setCurrentResponse((prev) => prev + data.content)
          break

        case 'function_call':
          setIsTyping(true)
          // Show function call in UI
          setMessages((prev) => [
            ...prev,
            {
              role: 'system',
              content: `Calling: ${data.function}`,
              type: 'function_call',
              data: data.arguments,
            },
          ])
          break

        case 'function_result':
          // Update function call with result
          setMessages((prev) => {
            const updated = [...prev]
            const lastFunctionCall = updated.findLastIndex(
              (m) => m.type === 'function_call'
            )
            if (lastFunctionCall !== -1) {
              updated[lastFunctionCall] = {
                ...updated[lastFunctionCall],
                result: data.result,
              }
            }
            return updated
          })
          break

        case 'complete':
          setIsTyping(false)
          if (data.full_response) {
            setMessages((prev) => [
              ...prev,
              { role: 'assistant', content: data.full_response },
            ])
          }
          setCurrentResponse('')
          break

        case 'error':
          setIsTyping(false)
          setMessages((prev) => [
            ...prev,
            { role: 'error', content: data.message },
          ])
          setCurrentResponse('')
          break

        case 'title_update':
          if (onTitleUpdate) {
            onTitleUpdate(data.title)
          }
          break

        default:
          console.log('Unknown message type:', data.type)
      }
    }

    ws.onclose = () => {
      setIsConnected(false)
      console.log('WebSocket disconnected')
      // Attempt to reconnect after 3 seconds
      reconnectTimeoutRef.current = setTimeout(() => {
        connect()
      }, 3000)
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }, [conversationId])

  useEffect(() => {
    connect()

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [connect])

  const sendMessage = useCallback((messageData) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      // Handle both string messages (legacy) and object messages with files
      const text = typeof messageData === 'string' ? messageData : messageData.text
      const files = typeof messageData === 'object' ? messageData.files : []

      // Add user message to UI with file indicators
      const userMessage = {
        role: 'user',
        content: text,
        files: files
      }
      setMessages((prev) => [...prev, userMessage])

      // Show thinking indicator immediately
      setIsTyping(true)

      // Send to WebSocket
      wsRef.current.send(JSON.stringify({
        message: text,
        files: files
      }))
    }
  }, [])

  return {
    isConnected,
    messages,
    isTyping,
    currentResponse,
    sendMessage,
    setMessages,
  }
}
