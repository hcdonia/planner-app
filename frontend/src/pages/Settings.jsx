import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'

function Settings() {
  const [activeTab, setActiveTab] = useState('status')
  const [settings, setSettings] = useState(null)
  const [systemStatus, setSystemStatus] = useState(null)
  const [googleCalendars, setGoogleCalendars] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const {
    getAllSettings,
    getGoogleCalendars,
    getSystemStatus,
    addCalendar,
    removeCalendar,
    updateCalendar,
    deleteKnowledge,
    deleteInstruction,
    deleteRule,
    initializeCalendars,
  } = useApi()

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      setLoading(true)
      const [settingsData, googleCals, status] = await Promise.all([
        getAllSettings(),
        getGoogleCalendars().catch(() => ({ calendars: [] })),
        getSystemStatus().catch(() => null),
      ])
      setSettings(settingsData)
      setGoogleCalendars(googleCals.calendars || [])
      setSystemStatus(status)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleAddCalendar = async (cal) => {
    try {
      await addCalendar({
        name: cal.name,
        google_calendar_id: cal.id,
        permission: 'read',
      })
      loadSettings()
    } catch (err) {
      alert('Failed to add calendar: ' + err.message)
    }
  }

  const handleRemoveCalendar = async (id) => {
    if (!confirm('Remove this calendar?')) return
    try {
      await removeCalendar(id)
      loadSettings()
    } catch (err) {
      alert('Failed to remove calendar: ' + err.message)
    }
  }

  const handleTogglePermission = async (cal) => {
    const newPermission = cal.permission === 'read' ? 'read_write' : 'read'
    try {
      await updateCalendar(cal.id, { permission: newPermission })
      loadSettings()
    } catch (err) {
      alert('Failed to update permission: ' + err.message)
    }
  }

  const handleDeleteKnowledge = async (id) => {
    if (!confirm('Delete this knowledge entry?')) return
    try {
      await deleteKnowledge(id)
      loadSettings()
    } catch (err) {
      alert('Failed to delete: ' + err.message)
    }
  }

  const handleDeleteInstruction = async (id) => {
    if (!confirm('Delete this instruction?')) return
    try {
      await deleteInstruction(id)
      loadSettings()
    } catch (err) {
      alert('Failed to delete: ' + err.message)
    }
  }

  const handleDeleteRule = async (id) => {
    if (!confirm('Delete this rule?')) return
    try {
      await deleteRule(id)
      loadSettings()
    } catch (err) {
      alert('Failed to delete: ' + err.message)
    }
  }

  const handleInitialize = async () => {
    try {
      await initializeCalendars()
      loadSettings()
    } catch (err) {
      alert('Failed to initialize: ' + err.message)
    }
  }

  const tabs = [
    { id: 'status', label: 'System Status' },
    { id: 'calendars', label: 'Calendars' },
    { id: 'knowledge', label: 'Knowledge' },
    { id: 'instructions', label: 'Instructions' },
    { id: 'rules', label: 'Rules' },
  ]

  const getStatusColor = (status) => {
    switch (status) {
      case 'ok':
      case 'configured':
      case 'connected':
      case 'ready':
        return 'bg-green-100 text-green-700'
      case 'needs_setup':
      case 'not_configured':
      case 'missing_credentials':
        return 'bg-yellow-100 text-yellow-700'
      case 'error':
      case 'invalid_key_format':
        return 'bg-red-100 text-red-700'
      default:
        return 'bg-gray-100 text-gray-700'
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'ok':
      case 'configured':
      case 'connected':
      case 'ready':
        return (
          <svg className="w-5 h-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        )
      case 'needs_setup':
      case 'not_configured':
      case 'missing_credentials':
        return (
          <svg className="w-5 h-5 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        )
      case 'error':
      case 'invalid_key_format':
        return (
          <svg className="w-5 h-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        )
      default:
        return (
          <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/" className="text-gray-500 hover:text-gray-700">
              <svg
                className="w-6 h-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 19l-7-7 7-7"
                />
              </svg>
            </Link>
            <h1 className="text-xl font-semibold text-gray-800">Settings</h1>
          </div>
          <button
            onClick={loadSettings}
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
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </button>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-6">
        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-gray-200">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                activeTab === tab.id
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {error && (
          <div className="bg-red-100 text-red-600 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* System Status Tab */}
        {activeTab === 'status' && (
          <div className="space-y-6">
            {/* Overall Status */}
            <div className={`rounded-lg border p-6 ${
              systemStatus?.overall === 'ready'
                ? 'bg-green-50 border-green-200'
                : 'bg-yellow-50 border-yellow-200'
            }`}>
              <div className="flex items-center gap-3">
                {systemStatus?.overall === 'ready' ? (
                  <svg className="w-8 h-8 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                ) : (
                  <svg className="w-8 h-8 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                )}
                <div>
                  <h2 className={`text-lg font-semibold ${
                    systemStatus?.overall === 'ready' ? 'text-green-700' : 'text-yellow-700'
                  }`}>
                    {systemStatus?.overall === 'ready' ? 'System Ready' : 'Setup Required'}
                  </h2>
                  <p className={`text-sm ${
                    systemStatus?.overall === 'ready' ? 'text-green-600' : 'text-yellow-600'
                  }`}>
                    {systemStatus?.overall === 'ready'
                      ? 'All systems are configured and working properly.'
                      : 'Some components need configuration before the AI can work fully.'}
                  </p>
                </div>
              </div>
            </div>

            {/* Individual Services */}
            <div className="bg-white rounded-lg border border-gray-200 divide-y divide-gray-200">
              {/* OpenAI Status */}
              <div className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {getStatusIcon(systemStatus?.openai?.status)}
                  <div>
                    <p className="font-medium text-gray-800">OpenAI API</p>
                    <p className="text-sm text-gray-500">Model: {systemStatus?.openai?.model || 'Unknown'}</p>
                  </div>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(systemStatus?.openai?.status)}`}>
                  {systemStatus?.openai?.status || 'unknown'}
                </span>
              </div>
              {systemStatus?.openai?.message && (
                <div className="px-4 py-2 bg-yellow-50 text-sm text-yellow-700">
                  {systemStatus.openai.message}
                </div>
              )}

              {/* Google Calendar Status */}
              <div className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {getStatusIcon(systemStatus?.google_calendar?.status)}
                  <div>
                    <p className="font-medium text-gray-800">Google Calendar</p>
                    <p className="text-sm text-gray-500">
                      {systemStatus?.google_calendar?.available_calendars
                        ? `${systemStatus.google_calendar.available_calendars} calendars available`
                        : 'Not connected'}
                    </p>
                  </div>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(systemStatus?.google_calendar?.status)}`}>
                  {systemStatus?.google_calendar?.status || 'unknown'}
                </span>
              </div>
              {systemStatus?.google_calendar?.message && (
                <div className="px-4 py-2 bg-yellow-50 text-sm text-yellow-700">
                  {systemStatus.google_calendar.message}
                </div>
              )}

              {/* Database Status */}
              <div className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {getStatusIcon(systemStatus?.database?.status)}
                  <div>
                    <p className="font-medium text-gray-800">Database</p>
                    <p className="text-sm text-gray-500">SQLite local storage</p>
                  </div>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(systemStatus?.database?.status)}`}>
                  {systemStatus?.database?.status || 'unknown'}
                </span>
              </div>

              {/* Configuration Summary */}
              <div className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {getStatusIcon(systemStatus?.calendars_configured > 0 ? 'ok' : 'not_configured')}
                  <div>
                    <p className="font-medium text-gray-800">Calendars Configured</p>
                    <p className="text-sm text-gray-500">
                      {systemStatus?.calendars_configured || 0} tracked,
                      {systemStatus?.writable_calendar ? ' with write access' : ' no write access'}
                    </p>
                  </div>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                  systemStatus?.calendars_configured > 0 && systemStatus?.writable_calendar
                    ? 'bg-green-100 text-green-700'
                    : 'bg-yellow-100 text-yellow-700'
                }`}>
                  {systemStatus?.calendars_configured || 0} calendars
                </span>
              </div>

              {/* Knowledge Entries */}
              <div className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <svg className="w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  <div>
                    <p className="font-medium text-gray-800">Knowledge Entries</p>
                    <p className="text-sm text-gray-500">What the AI knows about you</p>
                  </div>
                </div>
                <span className="px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                  {systemStatus?.knowledge_entries || 0} entries
                </span>
              </div>
            </div>

            {/* Troubleshooting Tips */}
            {systemStatus?.overall !== 'ready' && (
              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <h3 className="font-medium text-gray-800 mb-4">Troubleshooting</h3>
                <ul className="space-y-2 text-sm text-gray-600">
                  {systemStatus?.openai?.status !== 'configured' && (
                    <li className="flex items-start gap-2">
                      <span className="text-yellow-500">•</span>
                      <span>Add your OpenAI API key to the <code className="bg-gray-100 px-1 rounded">.env</code> file as <code className="bg-gray-100 px-1 rounded">OPENAI_API_KEY=sk-...</code></span>
                    </li>
                  )}
                  {systemStatus?.google_calendar?.status !== 'connected' && (
                    <li className="flex items-start gap-2">
                      <span className="text-yellow-500">•</span>
                      <span>Download <code className="bg-gray-100 px-1 rounded">credentials.json</code> from Google Cloud Console and place it in the project root</span>
                    </li>
                  )}
                  {!systemStatus?.writable_calendar && systemStatus?.calendars_configured > 0 && (
                    <li className="flex items-start gap-2">
                      <span className="text-yellow-500">•</span>
                      <span>Enable "Read & Write" permission on at least one calendar so the AI can schedule tasks</span>
                    </li>
                  )}
                  {systemStatus?.calendars_configured === 0 && (
                    <li className="flex items-start gap-2">
                      <span className="text-yellow-500">•</span>
                      <span>Go to the Calendars tab and add at least one calendar to track</span>
                    </li>
                  )}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Calendars Tab */}
        {activeTab === 'calendars' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-medium text-gray-800">Tracked Calendars</h3>
                <button
                  onClick={handleInitialize}
                  className="text-sm text-primary-500 hover:text-primary-600"
                >
                  Auto-detect calendars
                </button>
              </div>

              {settings?.calendars?.length === 0 ? (
                <p className="text-gray-500 text-sm">No calendars tracked yet</p>
              ) : (
                <div className="space-y-2">
                  {settings?.calendars?.map((cal) => (
                    <div
                      key={cal.id}
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                    >
                      <div className="flex-1">
                        <p className="font-medium text-gray-800">{cal.name}</p>
                        <p className="text-xs text-gray-400 truncate max-w-xs">{cal.google_calendar_id}</p>
                      </div>
                      <div className="flex items-center gap-3">
                        <button
                          onClick={() => handleTogglePermission(cal)}
                          className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${
                            cal.permission === 'read_write'
                              ? 'bg-green-100 text-green-700 hover:bg-green-200'
                              : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
                          }`}
                        >
                          {cal.permission === 'read_write' ? 'Read & Write' : 'Read Only'}
                        </button>
                        <button
                          onClick={() => handleRemoveCalendar(cal.id)}
                          className="text-red-500 hover:text-red-600"
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
                              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                            />
                          </svg>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h3 className="font-medium text-gray-800 mb-4">
                Available Google Calendars
              </h3>
              {googleCalendars.length === 0 ? (
                <p className="text-gray-500 text-sm">
                  Connect to Google Calendar to see available calendars
                </p>
              ) : (
                <div className="space-y-2">
                  {googleCalendars
                    .filter(
                      (gc) =>
                        !settings?.calendars?.some(
                          (tc) => tc.google_calendar_id === gc.id
                        )
                    )
                    .map((cal) => (
                      <div
                        key={cal.id}
                        className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                      >
                        <p className="text-gray-800">{cal.name}</p>
                        <button
                          onClick={() => handleAddCalendar(cal)}
                          className="text-primary-500 hover:text-primary-600"
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
                              d="M12 4v16m8-8H4"
                            />
                          </svg>
                        </button>
                      </div>
                    ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Knowledge Tab */}
        {activeTab === 'knowledge' && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="font-medium text-gray-800 mb-4">
              What the AI knows about you
            </h3>
            {settings?.knowledge?.length === 0 ? (
              <p className="text-gray-500 text-sm">
                No knowledge stored yet. Chat with the AI to teach it about you!
              </p>
            ) : (
              <div className="space-y-3">
                {settings?.knowledge?.map((k) => (
                  <div
                    key={k.id}
                    className="p-4 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <span className="text-xs text-primary-500 uppercase font-medium">
                          {k.category}
                        </span>
                        <p className="font-medium text-gray-800 mt-1">
                          {k.subject}
                        </p>
                        <p className="text-gray-600 text-sm mt-1">{k.content}</p>
                      </div>
                      <button
                        onClick={() => handleDeleteKnowledge(k.id)}
                        className="text-gray-400 hover:text-red-500"
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
                            d="M6 18L18 6M6 6l12 12"
                          />
                        </svg>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Instructions Tab */}
        {activeTab === 'instructions' && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="font-medium text-gray-800 mb-4">AI Behavior Instructions</h3>
            {settings?.instructions?.length === 0 ? (
              <p className="text-gray-500 text-sm">
                No instructions set. Tell the AI how you want it to behave!
              </p>
            ) : (
              <div className="space-y-3">
                {settings?.instructions?.map((inst) => (
                  <div
                    key={inst.id}
                    className="p-4 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <span className="text-xs text-primary-500 uppercase font-medium">
                          {inst.category}
                        </span>
                        <p className="text-gray-800 mt-1">{inst.instruction}</p>
                        <p className="text-xs text-gray-400 mt-1">
                          Source: {inst.source}
                        </p>
                      </div>
                      <button
                        onClick={() => handleDeleteInstruction(inst.id)}
                        className="text-gray-400 hover:text-red-500"
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
                            d="M6 18L18 6M6 6l12 12"
                          />
                        </svg>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Rules Tab */}
        {activeTab === 'rules' && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="font-medium text-gray-800 mb-4">Scheduling Rules</h3>
            {settings?.rules?.length === 0 ? (
              <p className="text-gray-500 text-sm">
                No scheduling rules set. Tell the AI about your preferences!
              </p>
            ) : (
              <div className="space-y-3">
                {settings?.rules?.map((rule) => (
                  <div
                    key={rule.id}
                    className="p-4 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <span className="text-xs text-primary-500 uppercase font-medium">
                          {rule.rule_type}
                        </span>
                        <p className="font-medium text-gray-800 mt-1">{rule.name}</p>
                        <pre className="text-xs text-gray-500 mt-1 bg-gray-100 p-2 rounded">
                          {JSON.stringify(rule.config, null, 2)}
                        </pre>
                      </div>
                      <button
                        onClick={() => handleDeleteRule(rule.id)}
                        className="text-gray-400 hover:text-red-500"
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
                            d="M6 18L18 6M6 6l12 12"
                          />
                        </svg>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Patterns (read-only) */}
        {settings?.patterns?.patterns && Object.keys(settings.patterns.patterns).length > 0 && (
          <div className="mt-6 bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="font-medium text-gray-800 mb-4">Learned Patterns</h3>
            <p className="text-sm text-gray-500 mb-3">
              These patterns are automatically learned from your task history.
            </p>
            <pre className="text-sm bg-gray-50 p-4 rounded-lg overflow-x-auto">
              {JSON.stringify(settings.patterns, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}

export default Settings
