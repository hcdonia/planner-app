import { useRef, useEffect } from 'react'
import MessageBubble from './MessageBubble'

function TypingIndicator() {
  return (
    <div className="flex justify-start mb-4">
      <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-md px-4 py-3 shadow-sm">
        <div className="flex gap-1">
          <div className="w-2 h-2 bg-gray-400 rounded-full typing-dot" />
          <div className="w-2 h-2 bg-gray-400 rounded-full typing-dot" />
          <div className="w-2 h-2 bg-gray-400 rounded-full typing-dot" />
        </div>
      </div>
    </div>
  )
}

function StreamingMessage({ content }) {
  if (!content) return null

  return (
    <div className="flex justify-start mb-4">
      <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-md px-4 py-3 max-w-[80%] shadow-sm">
        <p className="whitespace-pre-wrap">{content}</p>
        <span className="inline-block w-2 h-4 bg-primary-500 animate-pulse ml-1" />
      </div>
    </div>
  )
}

function ChatContainer({ messages, isTyping, currentResponse }) {
  const containerRef = useRef(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [messages, currentResponse, isTyping])

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto px-4 py-6"
    >
      <div className="max-w-4xl mx-auto">
        {messages.length === 0 && !isTyping && (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg
                className="w-8 h-8 text-primary-500"
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
            </div>
            <h2 className="text-xl font-semibold text-gray-800 mb-2">
              AI Planning Assistant
            </h2>
            <p className="text-gray-500 max-w-md mx-auto">
              I can help you schedule tasks, check your calendar, and learn about your preferences to assist you better.
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-2">
              {[
                "What's on my calendar today?",
                "Schedule a meeting tomorrow at 2pm",
                "What calendars do you have access to?",
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  className="px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm text-gray-700 transition-colors"
                  onClick={() => {
                    // This would need to be passed as a prop
                    console.log('Suggestion clicked:', suggestion)
                  }}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message, index) => (
          <MessageBubble key={index} message={message} />
        ))}

        {currentResponse && <StreamingMessage content={currentResponse} />}

        {isTyping && !currentResponse && <TypingIndicator />}
      </div>
    </div>
  )
}

export default ChatContainer
