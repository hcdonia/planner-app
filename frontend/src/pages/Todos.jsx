import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'

function Todos() {
  const [todos, setTodos] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCompleted, setShowCompleted] = useState(false)
  const [newTodo, setNewTodo] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [editText, setEditText] = useState('')
  const [editingDateField, setEditingDateField] = useState(null) // {id, field}
  const [selectedTodo, setSelectedTodo] = useState(null) // For notes modal
  const [editingNotes, setEditingNotes] = useState(false)
  const [notesText, setNotesText] = useState('')

  const { getTodos, createTodo, updateTodo, deleteTodo, toggleTodo } = useApi()

  // Format date for display
  const formatDate = (dateStr) => {
    if (!dateStr) return null
    const date = new Date(dateStr)
    const today = new Date()
    const tomorrow = new Date(today)
    tomorrow.setDate(tomorrow.getDate() + 1)

    if (date.toDateString() === today.toDateString()) return 'Today'
    if (date.toDateString() === tomorrow.toDateString()) return 'Tomorrow'

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  // Format date for input field
  const formatDateForInput = (dateStr) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    return date.toISOString().split('T')[0]
  }

  useEffect(() => {
    loadTodos()
  }, [showCompleted])

  const loadTodos = async () => {
    try {
      setLoading(true)
      const data = await getTodos(showCompleted ? null : false)
      setTodos(data)
    } catch (err) {
      console.error('Failed to load todos:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleAddTodo = async (e) => {
    e.preventDefault()
    if (!newTodo.trim()) return

    try {
      await createTodo({ title: newTodo.trim() })
      setNewTodo('')
      loadTodos()
    } catch (err) {
      alert('Failed to add todo: ' + err.message)
    }
  }

  const handleToggle = async (id) => {
    try {
      await toggleTodo(id)
      loadTodos()
    } catch (err) {
      alert('Failed to update todo: ' + err.message)
    }
  }

  const handleDelete = async (id) => {
    try {
      await deleteTodo(id)
      loadTodos()
    } catch (err) {
      alert('Failed to delete todo: ' + err.message)
    }
  }

  const handleEdit = (todo) => {
    setEditingId(todo.id)
    setEditText(todo.title)
  }

  const handleSaveEdit = async (id) => {
    if (!editText.trim()) return
    try {
      await updateTodo(id, { title: editText.trim() })
      setEditingId(null)
      loadTodos()
    } catch (err) {
      alert('Failed to update todo: ' + err.message)
    }
  }

  const handlePriorityChange = async (id, priority) => {
    try {
      await updateTodo(id, { priority })
      loadTodos()
    } catch (err) {
      alert('Failed to update priority: ' + err.message)
    }
  }

  const handleDateChange = async (id, field, value) => {
    try {
      const update = {}
      update[field] = value ? new Date(value).toISOString() : null
      await updateTodo(id, update)
      setEditingDateField(null)
      loadTodos()
    } catch (err) {
      alert('Failed to update date: ' + err.message)
    }
  }

  const openNotes = (todo) => {
    setSelectedTodo(todo)
    setNotesText(todo.description || '')
    setEditingNotes(false)
  }

  const closeNotes = () => {
    setSelectedTodo(null)
    setEditingNotes(false)
    setNotesText('')
  }

  const handleSaveNotes = async () => {
    if (!selectedTodo) return
    try {
      await updateTodo(selectedTodo.id, { description: notesText })
      setEditingNotes(false)
      loadTodos()
      // Update the selected todo with new description
      setSelectedTodo({ ...selectedTodo, description: notesText })
    } catch (err) {
      alert('Failed to save notes: ' + err.message)
    }
  }

  const priorityColors = {
    high: 'bg-red-100 text-red-700 border-red-200',
    medium: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    low: 'bg-green-100 text-green-700 border-green-200',
  }

  const incompleteTodos = todos.filter(t => !t.completed)
  const completedTodos = todos.filter(t => t.completed)

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-2xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/" className="text-gray-500 hover:text-gray-700">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <h1 className="text-xl font-semibold text-gray-800">To-Do List</h1>
          </div>
          <button
            onClick={() => setShowCompleted(!showCompleted)}
            className={`text-sm px-3 py-1 rounded-full ${
              showCompleted ? 'bg-primary-100 text-primary-700' : 'bg-gray-100 text-gray-600'
            }`}
          >
            {showCompleted ? 'Hide Completed' : 'Show Completed'}
          </button>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-6 pb-safe">
        {/* Add Todo Form */}
        <form onSubmit={handleAddTodo} className="mb-6">
          <div className="flex gap-2">
            <input
              type="text"
              value={newTodo}
              onChange={(e) => setNewTodo(e.target.value)}
              placeholder="Add a new task..."
              className="flex-1 px-4 py-3 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
            <button
              type="submit"
              className="px-6 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
            >
              Add
            </button>
          </div>
        </form>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary-500"></div>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Active Todos */}
            <div className="bg-white rounded-lg border border-gray-200 divide-y divide-gray-100">
              {incompleteTodos.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  <svg className="w-12 h-12 mx-auto mb-3 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <p>All done! Add a new task above.</p>
                </div>
              ) : (
                incompleteTodos.map((todo) => (
                  <div key={todo.id} className="p-3 sm:p-4 flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3 group">
                    <div className="flex items-start sm:items-center gap-3 flex-1 min-w-0">
                      <button
                        onClick={() => handleToggle(todo.id)}
                        className="w-6 h-6 mt-0.5 sm:mt-0 flex-shrink-0 rounded-full border-2 border-gray-300 hover:border-primary-500 flex items-center justify-center transition-colors"
                      >
                        <svg className="w-4 h-4 text-gray-300 group-hover:text-primary-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      </button>

                      <div className="flex-1 min-w-0">
                        {editingId === todo.id ? (
                          <input
                            type="text"
                            value={editText}
                            onChange={(e) => setEditText(e.target.value)}
                            onBlur={() => handleSaveEdit(todo.id)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSaveEdit(todo.id)}
                            className="w-full px-2 py-1 border border-primary-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                            autoFocus
                          />
                        ) : (
                          <div className="flex items-center gap-2">
                            <span
                              className="text-gray-800 cursor-pointer break-words hover:text-primary-600"
                              onClick={() => openNotes(todo)}
                            >
                              {todo.title}
                            </span>
                            {todo.description && (
                              <svg className="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                              </svg>
                            )}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Dates and controls row */}
                    <div className="flex flex-wrap items-center gap-2 pl-9 sm:pl-0">
                      {/* Start Date */}
                      {editingDateField?.id === todo.id && editingDateField?.field === 'start_date' ? (
                        <input
                          type="date"
                          defaultValue={formatDateForInput(todo.start_date)}
                          onChange={(e) => handleDateChange(todo.id, 'start_date', e.target.value)}
                          onBlur={() => setEditingDateField(null)}
                          className="px-2 py-1 text-xs border border-primary-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                          autoFocus
                        />
                      ) : (
                        <button
                          onClick={() => setEditingDateField({ id: todo.id, field: 'start_date' })}
                          className={`px-2 py-1 text-xs rounded border ${
                            todo.start_date
                              ? 'bg-blue-50 text-blue-600 border-blue-200'
                              : 'bg-gray-50 text-gray-400 border-gray-200 border-dashed'
                          }`}
                        >
                          {todo.start_date ? `Start: ${formatDate(todo.start_date)}` : '+ Start'}
                        </button>
                      )}

                      {/* Due Date */}
                      {editingDateField?.id === todo.id && editingDateField?.field === 'due_date' ? (
                        <input
                          type="date"
                          defaultValue={formatDateForInput(todo.due_date)}
                          onChange={(e) => handleDateChange(todo.id, 'due_date', e.target.value)}
                          onBlur={() => setEditingDateField(null)}
                          className="px-2 py-1 text-xs border border-primary-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                          autoFocus
                        />
                      ) : (
                        <button
                          onClick={() => setEditingDateField({ id: todo.id, field: 'due_date' })}
                          className={`px-2 py-1 text-xs rounded border ${
                            todo.due_date
                              ? 'bg-orange-50 text-orange-600 border-orange-200'
                              : 'bg-gray-50 text-gray-400 border-gray-200 border-dashed'
                          }`}
                        >
                          {todo.due_date ? `Due: ${formatDate(todo.due_date)}` : '+ Due'}
                        </button>
                      )}

                      {/* Priority */}
                      <select
                        value={todo.priority}
                        onChange={(e) => handlePriorityChange(todo.id, e.target.value)}
                        className={`px-2 py-1 text-xs font-medium rounded border ${priorityColors[todo.priority]}`}
                      >
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                      </select>

                      {/* Delete */}
                      <button
                        onClick={() => handleDelete(todo.id)}
                        className="sm:opacity-0 sm:group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-all p-1"
                      >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Completed Todos */}
            {showCompleted && completedTodos.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-2">Completed ({completedTodos.length})</h3>
                <div className="bg-white rounded-lg border border-gray-200 divide-y divide-gray-100">
                  {completedTodos.map((todo) => (
                    <div key={todo.id} className="p-4 flex items-center gap-3 group">
                      <button
                        onClick={() => handleToggle(todo.id)}
                        className="w-6 h-6 rounded-full bg-primary-500 flex items-center justify-center"
                      >
                        <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      </button>
                      <span className="flex-1 text-gray-400 line-through">{todo.title}</span>
                      <button
                        onClick={() => handleDelete(todo.id)}
                        className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-all"
                      >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Notes Modal */}
      {selectedTodo && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full max-h-[80vh] flex flex-col">
            {/* Modal Header */}
            <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
              <div className="flex-1 min-w-0">
                <h3 className="font-medium text-gray-800 truncate">{selectedTodo.title}</h3>
                <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                  {selectedTodo.start_date && (
                    <span className="text-blue-600">Start: {formatDate(selectedTodo.start_date)}</span>
                  )}
                  {selectedTodo.due_date && (
                    <span className="text-orange-600">Due: {formatDate(selectedTodo.due_date)}</span>
                  )}
                </div>
              </div>
              <button
                onClick={closeNotes}
                className="text-gray-400 hover:text-gray-600 p-1"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 p-4 overflow-y-auto">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-600">Notes</span>
                {!editingNotes && (
                  <button
                    onClick={() => setEditingNotes(true)}
                    className="text-xs text-primary-600 hover:text-primary-700"
                  >
                    Edit
                  </button>
                )}
              </div>

              {editingNotes ? (
                <textarea
                  value={notesText}
                  onChange={(e) => setNotesText(e.target.value)}
                  placeholder="Add notes about this task..."
                  className="w-full h-48 px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
                  autoFocus
                />
              ) : (
                <div className="min-h-[120px] p-3 bg-gray-50 rounded-lg text-gray-700 whitespace-pre-wrap">
                  {selectedTodo.description || (
                    <span className="text-gray-400 italic">No notes yet. Click Edit to add notes.</span>
                  )}
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="px-4 py-3 border-t border-gray-200 flex justify-end gap-2">
              {editingNotes ? (
                <>
                  <button
                    onClick={() => {
                      setEditingNotes(false)
                      setNotesText(selectedTodo.description || '')
                    }}
                    className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSaveNotes}
                    className="px-4 py-2 text-sm bg-primary-500 text-white rounded-lg hover:bg-primary-600"
                  >
                    Save Notes
                  </button>
                </>
              ) : (
                <button
                  onClick={closeNotes}
                  className="px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
                >
                  Close
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Todos
