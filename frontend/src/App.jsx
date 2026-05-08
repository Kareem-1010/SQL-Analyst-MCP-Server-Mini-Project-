import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect, createContext, useContext } from 'react'
import LandingPage from './pages/LandingPage'
import AuthPage from './pages/AuthPage'
import Dashboard from './pages/Dashboard'
import UploadPage from './pages/UploadPage'
import ChatPage from './pages/ChatPage'
import VisualizationPage from './pages/VisualizationPage'
import QueryHistoryPage from './pages/QueryHistoryPage'
import { ToastProvider } from './components/Toast'

export const ThemeContext = createContext()
export const useTheme = () => useContext(ThemeContext)

const PrivateRoute = ({ children }) => {
  const token = localStorage.getItem('sql_analyst_token')
  return token ? children : <Navigate to="/auth" replace />
}

export default function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark')

  useEffect(() => {
    document.documentElement.className = theme
    localStorage.setItem('theme', theme)
  }, [theme])

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark')

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/"          element={<LandingPage />} />
            <Route path="/auth"      element={<AuthPage />} />
            <Route path="/dashboard" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
            <Route path="/upload"    element={<PrivateRoute><UploadPage /></PrivateRoute>} />
            <Route path="/chat"      element={<PrivateRoute><ChatPage /></PrivateRoute>} />
            <Route path="/visualize" element={<PrivateRoute><VisualizationPage /></PrivateRoute>} />
            <Route path="/history"   element={<PrivateRoute><QueryHistoryPage /></PrivateRoute>} />
            <Route path="*"          element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </ThemeContext.Provider>
  )
}

