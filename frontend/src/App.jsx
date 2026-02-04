import { Routes, Route } from 'react-router-dom'
import Chat from './pages/Chat'
import Settings from './pages/Settings'
import Todos from './pages/Todos'
import { ConnectionProvider } from './components/ConnectionStatus'

function App() {
  return (
    <ConnectionProvider>
      <div className="min-h-screen bg-gray-50">
        <Routes>
          <Route path="/" element={<Chat />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/todos" element={<Todos />} />
        </Routes>
      </div>
    </ConnectionProvider>
  )
}

export default App
