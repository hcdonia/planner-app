import { useState, useEffect } from 'react'
import { useApi } from '../hooks/useApi'

function CalendarSidebar() {
  const [schedule, setSchedule] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const { getTodaySchedule } = useApi()

  useEffect(() => {
    loadSchedule()
  }, [])

  const loadSchedule = async () => {
    try {
      setLoading(true)
      const data = await getTodaySchedule()
      setSchedule(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="w-80 bg-white border-l border-gray-200 p-4">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-32 mb-4" />
          <div className="space-y-3">
            <div className="h-16 bg-gray-100 rounded" />
            <div className="h-16 bg-gray-100 rounded" />
            <div className="h-16 bg-gray-100 rounded" />
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="w-80 bg-white border-l border-gray-200 p-4">
        <h3 className="font-semibold text-gray-800 mb-4">Today's Schedule</h3>
        <div className="text-red-500 text-sm">
          <p>Could not load schedule</p>
          <button
            onClick={loadSchedule}
            className="text-primary-500 hover:underline mt-2"
          >
            Try again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="w-80 bg-white border-l border-gray-200 p-4 overflow-y-auto">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-800">Today's Schedule</h3>
        <button
          onClick={loadSchedule}
          className="text-gray-400 hover:text-gray-600"
        >
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
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
        </button>
      </div>

      {!schedule?.events || schedule.events.length === 0 ? (
        <div className="text-center py-8">
          <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
            <svg
              className="w-6 h-6 text-green-500"
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
          </div>
          <p className="text-gray-500 text-sm">No events scheduled today</p>
          <p className="text-gray-400 text-xs mt-1">Your day is clear!</p>
        </div>
      ) : (
        <div className="space-y-3">
          {schedule.events.map((event, index) => {
            const startTime = new Date(event.start)
            const endTime = new Date(event.end)
            const isNow =
              new Date() >= startTime && new Date() <= endTime
            const isPast = new Date() > endTime

            return (
              <div
                key={index}
                className={`p-3 rounded-lg border ${
                  isNow
                    ? 'border-primary-500 bg-primary-50'
                    : isPast
                    ? 'border-gray-200 bg-gray-50 opacity-60'
                    : 'border-gray-200 bg-white'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-800 truncate">
                      {event.title}
                    </p>
                    <p className="text-sm text-gray-500">
                      {startTime.toLocaleTimeString([], {
                        hour: 'numeric',
                        minute: '2-digit',
                      })}{' '}
                      -{' '}
                      {endTime.toLocaleTimeString([], {
                        hour: 'numeric',
                        minute: '2-digit',
                      })}
                    </p>
                  </div>
                  {isNow && (
                    <span className="flex-shrink-0 text-xs bg-primary-500 text-white px-2 py-1 rounded-full">
                      Now
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      <div className="mt-6 pt-4 border-t border-gray-200">
        <p className="text-xs text-gray-400 text-center">
          {new Date().toLocaleDateString(undefined, {
            weekday: 'long',
            month: 'long',
            day: 'numeric',
          })}
        </p>
      </div>
    </div>
  )
}

export default CalendarSidebar
