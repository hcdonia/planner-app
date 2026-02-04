import { useState, useEffect, useCallback } from 'react'
import Sidebar from '../components/Sidebar'
import ChatContainer from '../components/ChatContainer'
import InputBar from '../components/InputBar'
import CalendarSidebar from '../components/CalendarSidebar'
import { useWebSocket } from '../hooks/useWebSocket'
import { useApi } from '../hooks/useApi'

function Chat() {
  const [conversationId, setConversationId] = useState(null)
  const [conversationTitle, setConversationTitle] = useState(null)
  const [conversations, setConversations] = useState([])
  const [showCalendar, setShowCalendar] = useState(true)

  const { createConversation, getConversations, getConversation, deleteConversation } = useApi()

  // Callback for when conversation title is auto-generated
  const handleTitleUpdate = useCallback((title) => {
    setConversationTitle(title)
    loadConversations()
  }, [])

  const {
    isConnected,
    messages,
    isTyping,
    currentResponse,
    sendMessage,
    setMessages,
  } = useWebSocket(conversationId, handleTitleUpdate)

  // Load conversations on mount
  useEffect(() => {
    loadConversations()
  }, [])

  const loadConversations = async () => {
    try {
      const data = await getConversations()
      setConversations(data)
    } catch (err) {
      console.error('Failed to load conversations:', err)
    }
  }

  const handleNewChat = async () => {
    try {
      const conv = await createConversation()
      setConversationId(conv.id)
      setConversationTitle(null)
      setMessages([])
      loadConversations()
    } catch (err) {
      console.error('Failed to create conversation:', err)
    }
  }

  const handleSelectConversation = async (id) => {
    try {
      const conv = await getConversation(id)
      setConversationId(id)
      setConversationTitle(conv.title)
      // Load existing messages
      setMessages(
        conv.messages.map((m) => ({
          role: m.role,
          content: m.content,
          extra_data: m.extra_data,
        }))
      )
    } catch (err) {
      console.error('Failed to load conversation:', err)
    }
  }

  const handleSend = useCallback(
    (message) => {
      if (!conversationId) {
        // Create new conversation first
        createConversation()
          .then((conv) => {
            setConversationId(conv.id)
            loadConversations()
            // Send message after a short delay to allow WebSocket to connect
            setTimeout(() => sendMessage(message), 500)
          })
          .catch((err) => console.error('Failed to create conversation:', err))
      } else {
        sendMessage(message)
      }
    },
    [conversationId, sendMessage, createConversation]
  )

  const handleDeleteConversation = async (id) => {
    try {
      await deleteConversation(id)
      if (conversationId === id) {
        setConversationId(null)
        setConversationTitle(null)
        setMessages([])
      }
      loadConversations()
    } catch (err) {
      console.error('Failed to delete conversation:', err)
    }
  }

  // Auto-create conversation if none exists
  useEffect(() => {
    if (!conversationId && conversations.length === 0) {
      // Don't auto-create, let user start fresh
    } else if (!conversationId && conversations.length > 0) {
      // Optionally load most recent
      // handleSelectConversation(conversations[0].id)
    }
  }, [conversationId, conversations])

  return (
    <div className="flex h-screen">
      <Sidebar
        conversations={conversations}
        onNewChat={handleNewChat}
        onSelectConversation={handleSelectConversation}
        onDeleteConversation={handleDeleteConversation}
        currentConversationId={conversationId}
      />

      <div className="flex-1 flex flex-col bg-gray-50">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="font-medium text-gray-800">
              {conversationTitle || (conversationId ? 'New Chat' : 'New Chat')}
            </h2>
            <span
              className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-green-400' : 'bg-gray-300'
              }`}
            />
          </div>
          <button
            onClick={() => setShowCalendar(!showCalendar)}
            className="text-gray-500 hover:text-gray-700"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
          </button>
        </div>

        {/* Chat Area */}
        <ChatContainer
          messages={messages}
          isTyping={isTyping}
          currentResponse={currentResponse}
        />

        {/* Input */}
        <InputBar
          onSend={handleSend}
          disabled={!isConnected && conversationId}
          placeholder={
            conversationId
              ? 'Type a message...'
              : 'Start typing to begin a new conversation...'
          }
        />
      </div>

      {/* Calendar Sidebar */}
      {showCalendar && <CalendarSidebar />}
    </div>
  )
}

export default Chat
