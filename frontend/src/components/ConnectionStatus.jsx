import { useState, useEffect, createContext, useContext } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const ConnectionContext = createContext({ isConnected: true, isConnecting: false })

export function useConnection() {
  return useContext(ConnectionContext)
}

export function ConnectionProvider({ children }) {
  const [isConnected, setIsConnected] = useState(true)
  const [isConnecting, setIsConnecting] = useState(true)
  const [showBanner, setShowBanner] = useState(false)

  useEffect(() => {
    let timeoutId

    const checkConnection = async () => {
      setIsConnecting(true)

      // Show banner after 3 seconds if still connecting
      timeoutId = setTimeout(() => {
        setShowBanner(true)
      }, 3000)

      try {
        const response = await fetch(`${API_BASE}/health`, {
          method: 'GET',
          signal: AbortSignal.timeout(60000), // 60 second timeout for cold starts
        })

        if (response.ok) {
          setIsConnected(true)
        } else {
          setIsConnected(false)
        }
      } catch (err) {
        setIsConnected(false)
      } finally {
        clearTimeout(timeoutId)
        setIsConnecting(false)
        setShowBanner(false)
      }
    }

    checkConnection()

    return () => {
      clearTimeout(timeoutId)
    }
  }, [])

  return (
    <ConnectionContext.Provider value={{ isConnected, isConnecting }}>
      {showBanner && isConnecting && (
        <div className="fixed top-0 left-0 right-0 bg-primary-500 text-white py-3 px-4 text-center z-50 flex items-center justify-center gap-3">
          <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span>Waking up server... This may take up to 30 seconds</span>
        </div>
      )}
      {!isConnecting && !isConnected && (
        <div className="fixed top-0 left-0 right-0 bg-red-500 text-white py-3 px-4 text-center z-50">
          Unable to connect to server. Please check your internet connection.
        </div>
      )}
      {children}
    </ConnectionContext.Provider>
  )
}
