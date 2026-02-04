import ReactMarkdown from 'react-markdown'

function MessageBubble({ message }) {
  const { role, content, type, result } = message

  // Function call message
  if (type === 'function_call') {
    return (
      <div className="flex justify-center my-2 message-enter">
        <div className="bg-gray-100 rounded-lg px-4 py-2 text-sm text-gray-600 max-w-md">
          <div className="flex items-center gap-2">
            <svg
              className="w-4 h-4 text-primary-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
            <span>{content}</span>
            {result?.success && (
              <svg
                className="w-4 h-4 text-green-500"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            )}
          </div>
        </div>
      </div>
    )
  }

  // Error message
  if (role === 'error') {
    return (
      <div className="flex justify-center my-2 message-enter">
        <div className="bg-red-100 rounded-lg px-4 py-2 text-sm text-red-600 max-w-md">
          <div className="flex items-center gap-2">
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span>{content}</span>
          </div>
        </div>
      </div>
    )
  }

  // User message
  if (role === 'user') {
    return (
      <div className="flex justify-end mb-4 message-enter">
        <div className="bg-primary-500 text-white rounded-2xl rounded-tr-md px-4 py-3 max-w-[80%]">
          <p className="whitespace-pre-wrap">{content}</p>
        </div>
      </div>
    )
  }

  // Assistant message
  return (
    <div className="flex justify-start mb-4 message-enter">
      <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-md px-4 py-3 max-w-[80%] shadow-sm">
        <div className="markdown-content prose prose-sm max-w-none">
          <ReactMarkdown>{content}</ReactMarkdown>
        </div>
      </div>
    </div>
  )
}

export default MessageBubble
