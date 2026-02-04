import { useState, useCallback } from 'react'

// Use environment variable for API URL, fallback to localhost
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function useApi() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const request = useCallback(async (endpoint, options = {}) => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      setLoading(false)
      return data
    } catch (err) {
      setError(err.message)
      setLoading(false)
      throw err
    }
  }, [])

  // Conversation endpoints
  const createConversation = useCallback(
    (title) => request('/chat/conversations', {
      method: 'POST',
      body: JSON.stringify({ title }),
    }),
    [request]
  )

  const getConversations = useCallback(
    () => request('/chat/conversations'),
    [request]
  )

  const getConversation = useCallback(
    (id) => request(`/chat/conversations/${id}`),
    [request]
  )

  const deleteConversation = useCallback(
    (id) => request(`/chat/conversations/${id}`, { method: 'DELETE' }),
    [request]
  )

  // Calendar endpoints
  const getTodaySchedule = useCallback(
    () => request('/calendar/schedule/today'),
    [request]
  )

  const getWeekOverview = useCallback(
    () => request('/calendar/week'),
    [request]
  )

  const getTrackedCalendars = useCallback(
    () => request('/calendar/tracked'),
    [request]
  )

  const getGoogleCalendars = useCallback(
    () => request('/calendar/google-calendars'),
    [request]
  )

  const addCalendar = useCallback(
    (calendar) => request('/calendar/tracked', {
      method: 'POST',
      body: JSON.stringify(calendar),
    }),
    [request]
  )

  const removeCalendar = useCallback(
    (id) => request(`/calendar/tracked/${id}`, { method: 'DELETE' }),
    [request]
  )

  const updateCalendar = useCallback(
    (id, updates) => request(`/calendar/tracked/${id}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    }),
    [request]
  )

  // Knowledge endpoints
  const getKnowledge = useCallback(
    () => request('/knowledge/'),
    [request]
  )

  const createKnowledge = useCallback(
    (knowledge) => request('/knowledge/', {
      method: 'POST',
      body: JSON.stringify(knowledge),
    }),
    [request]
  )

  const deleteKnowledge = useCallback(
    (id) => request(`/knowledge/${id}`, { method: 'DELETE' }),
    [request]
  )

  // Instructions endpoints
  const getInstructions = useCallback(
    () => request('/knowledge/instructions'),
    [request]
  )

  const createInstruction = useCallback(
    (instruction) => request('/knowledge/instructions', {
      method: 'POST',
      body: JSON.stringify(instruction),
    }),
    [request]
  )

  const deleteInstruction = useCallback(
    (id) => request(`/knowledge/instructions/${id}`, { method: 'DELETE' }),
    [request]
  )

  // Rules endpoints
  const getRules = useCallback(
    () => request('/knowledge/rules'),
    [request]
  )

  const createRule = useCallback(
    (rule) => request('/knowledge/rules', {
      method: 'POST',
      body: JSON.stringify(rule),
    }),
    [request]
  )

  const deleteRule = useCallback(
    (id) => request(`/knowledge/rules/${id}`, { method: 'DELETE' }),
    [request]
  )

  // Settings endpoints
  const getAllSettings = useCallback(
    () => request('/settings/all'),
    [request]
  )

  const initializeCalendars = useCallback(
    () => request('/settings/initialize', { method: 'POST' }),
    [request]
  )

  const getSystemStatus = useCallback(
    () => request('/settings/status'),
    [request]
  )

  // Todo endpoints
  const getTodos = useCallback(
    (completed = null) => {
      const params = completed !== null ? `?completed=${completed}` : ''
      return request(`/todos/${params}`)
    },
    [request]
  )

  const createTodo = useCallback(
    (todo) => request('/todos/', {
      method: 'POST',
      body: JSON.stringify(todo),
    }),
    [request]
  )

  const updateTodo = useCallback(
    (id, updates) => request(`/todos/${id}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    }),
    [request]
  )

  const deleteTodo = useCallback(
    (id) => request(`/todos/${id}`, { method: 'DELETE' }),
    [request]
  )

  const toggleTodo = useCallback(
    (id) => request(`/todos/${id}/toggle`, { method: 'POST' }),
    [request]
  )

  return {
    loading,
    error,
    // Conversations
    createConversation,
    getConversations,
    getConversation,
    deleteConversation,
    // Calendar
    getTodaySchedule,
    getWeekOverview,
    getTrackedCalendars,
    getGoogleCalendars,
    addCalendar,
    removeCalendar,
    updateCalendar,
    // Knowledge
    getKnowledge,
    createKnowledge,
    deleteKnowledge,
    // Instructions
    getInstructions,
    createInstruction,
    deleteInstruction,
    // Rules
    getRules,
    createRule,
    deleteRule,
    // Settings
    getAllSettings,
    initializeCalendars,
    getSystemStatus,
    // Todos
    getTodos,
    createTodo,
    updateTodo,
    deleteTodo,
    toggleTodo,
  }
}
