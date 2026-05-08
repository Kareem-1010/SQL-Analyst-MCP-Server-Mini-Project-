import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 90000,
  headers: { 'Content-Type': 'application/json' },
})

// ── Auth token interceptor ───────────────────────────────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('sql_analyst_token')
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

// ── 401 interceptor — redirect to /auth on expired token ────────────────────
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('sql_analyst_token')
      localStorage.removeItem('sql_analyst_user')
      window.location.href = '/auth'
    }
    return Promise.reject(err)
  }
)

// ── Auth endpoints ───────────────────────────────────────────────────────────
export const loginUser = (username, password) =>
  api.post('/auth/login', { username, password })

export const registerUser = (username, password, display_name = '') =>
  api.post('/auth/register', { username, password, display_name })

export const getMe = () => api.get('/auth/me')

// ── Data endpoints ───────────────────────────────────────────────────────────
export const uploadFile = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const getTables = () => api.get('/tables')
export const describeTable = (tableName) => api.get(`/tables/${tableName}`)
export const getTableStats = (tableName) => api.get(`/tables/${tableName}/stats`)
export const deleteTable = (tableName) => api.delete(`/tables/${tableName}`)

// ── Query endpoints ──────────────────────────────────────────────────────────
export const runQuery = (question, tableName = null, conversationHistory = [], includeInsights = false) =>
  api.post('/query', {
    question,
    table_name: tableName,
    conversation_history: conversationHistory,
    include_insights: includeInsights,
  })

export const getQueryInsights = (sql, rows, columns, rowCount) =>
  api.post('/query/insights', { sql, rows, columns, row_count: rowCount })

export const suggestQueries = (tableName) =>
  api.post('/query/suggest', { table_name: tableName })

// SSE Streaming query — returns an EventSource-compatible fetch stream
export const streamQuery = (question, tableName = null) => {
  const token = localStorage.getItem('sql_analyst_token')
  return fetch('/api/query/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ question, table_name: tableName }),
  })
}

// ── History & Analytics ──────────────────────────────────────────────────────
export const getHistory = (limit = 50) => api.get(`/history?limit=${limit}`)
export const getAnalytics = () => api.get('/analytics')

// ── MCP tools ───────────────────────────────────────────────────────────────
export const callMCPTool = (toolName, params = {}) =>
  api.post(`/mcp/${toolName}`, { params })

export const getMCPTools = () => api.get('/mcp/tools')

// ── System ──────────────────────────────────────────────────────────────────
export const getSystemInfo = () => api.get('/system/info')

export default api

