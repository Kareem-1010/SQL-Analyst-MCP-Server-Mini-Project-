import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Database, Upload, MessageSquare, History, LogOut,
  Table2, Sun, Moon, BarChart2, Zap, TrendingUp,
  CheckCircle, AlertCircle, Clock, Command
} from 'lucide-react'
import {
  AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts'
import { getTables, getAnalytics } from '../services/api'
import { useTheme } from '../App'
import CommandPalette from '../components/CommandPalette'

const COLORS = ['#4f8ef7', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444']

const NavItem = ({ to, icon, label, active }) => (
  <Link
    to={to}
    className={`flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm transition-all ${
      active
        ? 'gradient-bg text-white font-medium'
        : 'text-secondary hover:text-primary glass-hover glass'
    }`}
  >
    {icon} {label}
  </Link>
)

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="glass rounded-xl px-3 py-2 border border-glass text-xs">
      <p className="text-secondary mb-1">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }}>{p.name}: {p.value}</p>
      ))}
    </div>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { theme, toggleTheme } = useTheme()
  const [tables, setTables] = useState([])
  const [analytics, setAnalytics] = useState(null)
  const [user, setUser] = useState({ username: 'User' })
  const [paletteOpen, setPaletteOpen] = useState(false)

  useEffect(() => {
    const u = localStorage.getItem('sql_analyst_user')
    if (u) {
      try { setUser(JSON.parse(u)) } catch (_) {}
    }
    getTables().then(r => setTables(r.data.tables || [])).catch(() => {})
    getAnalytics().then(r => setAnalytics(r.data)).catch(() => {})
  }, [])

  // Ctrl+K to open palette
  useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); setPaletteOpen(true) }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const logout = () => {
    localStorage.removeItem('sql_analyst_token')
    localStorage.removeItem('sql_analyst_user')
    navigate('/')
  }

  const displayName = user.username || user.name || 'User'
  const statCards = [
    { label: 'Tables Loaded',  value: analytics?.table_count ?? tables.length, icon: <Table2 size={20} />,   color: 'text-blue-400' },
    { label: 'Queries Run',    value: analytics?.total_queries ?? '—',          icon: <Zap size={20} />,     color: 'text-purple-400' },
    { label: 'Success Rate',   value: analytics ? `${analytics.success_rate}%` : '—', icon: <CheckCircle size={20} />, color: 'text-green-400' },
    { label: 'Avg Query Time', value: analytics ? `${Math.round(analytics.avg_exec_ms)}ms` : '—', icon: <Clock size={20} />, color: 'text-cyan-400' },
  ]

  // Prepare timeline data
  const timelineData = (analytics?.timeline || []).map(d => ({
    day: d.day?.slice(5) ?? d.day,
    Success: d.success,
    Errors: d.error,
  }))

  // Query type pie
  const typeData = (analytics?.query_types || []).map(t => ({
    name: t.type,
    value: t.count,
  }))

  return (
    <div className="min-h-screen bg-primary flex">
      <CommandPalette isOpen={paletteOpen} onClose={() => setPaletteOpen(false)} />

      {/* Sidebar */}
      <aside className="w-64 glass border-r border-glass flex flex-col p-4 gap-2 shrink-0">
        <div className="flex items-center gap-3 px-4 py-3 mb-4">
          <div className="w-8 h-8 gradient-bg rounded-lg flex items-center justify-center">
            <Database size={16} className="text-white" />
          </div>
          <div>
            <p className="font-bold text-sm text-primary">QueryMind AI</p>
            <p className="text-xs text-secondary">v3.0 Research</p>
          </div>
        </div>

        <NavItem to="/dashboard" icon={<BarChart2 size={16} />} label="Dashboard" active />
        <NavItem to="/upload"    icon={<Upload size={16} />}     label="Upload Data" />
        <NavItem to="/chat"      icon={<MessageSquare size={16} />} label="Chat Query" />
        <NavItem to="/visualize" icon={<BarChart2 size={16} />}  label="Visualize" />
        <NavItem to="/history"   icon={<History size={16} />}    label="Query History" />

        <div className="mt-auto flex flex-col gap-2">
          <button
            onClick={() => setPaletteOpen(true)}
            className="flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm text-secondary glass glass-hover"
          >
            <Command size={16} /> Command Palette
            <span className="ml-auto text-xs text-muted-custom">Ctrl+K</span>
          </button>
          <button
            onClick={toggleTheme}
            className="flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm text-secondary glass glass-hover"
          >
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
            {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
          </button>
          <button
            onClick={logout}
            className="flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm text-red-400 glass glass-hover"
          >
            <LogOut size={16} /> Sign Out
          </button>
          <div className="px-4 py-3 glass rounded-xl mt-2">
            <p className="text-sm font-medium text-primary truncate">{displayName}</p>
            <p className="text-xs text-muted-custom truncate">Authenticated user</p>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 p-8 overflow-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          <div className="mb-8 flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-primary">Welcome back, {displayName} 👋</h1>
              <p className="text-secondary mt-1">AI-powered SQL analytics workspace</p>
            </div>
            <div className="flex items-center gap-2 glass px-3 py-1.5 rounded-full border border-green-500/20">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
              <span className="text-xs text-green-400 font-medium">System Online</span>
            </div>
          </div>

          {/* Stat Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            {statCards.map((s, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.05 }}
                className="glass rounded-2xl p-5 glass-hover"
              >
                <div className={`mb-3 ${s.color}`}>{s.icon}</div>
                <p className="text-2xl font-bold text-primary">{s.value}</p>
                <p className="text-sm text-secondary mt-1">{s.label}</p>
              </motion.div>
            ))}
          </div>

          {/* Charts row */}
          {analytics && (timelineData.length > 0 || typeData.length > 0) && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
              {/* Area chart — query timeline */}
              {timelineData.length > 0 && (
                <div className="lg:col-span-2 glass rounded-2xl p-6">
                  <h2 className="font-semibold text-primary mb-4 flex items-center gap-2">
                    <TrendingUp size={16} className="text-blue-400" /> Query Volume (14 days)
                  </h2>
                  <ResponsiveContainer width="100%" height={180}>
                    <AreaChart data={timelineData}>
                      <defs>
                        <linearGradient id="gradSuccess" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#4f8ef7" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#4f8ef7" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="gradError" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                      <XAxis dataKey="day" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                      <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
                      <Area type="monotone" dataKey="Success" stroke="#4f8ef7" fill="url(#gradSuccess)" strokeWidth={2} />
                      <Area type="monotone" dataKey="Errors"  stroke="#ef4444" fill="url(#gradError)"   strokeWidth={2} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* Pie chart — query types */}
              {typeData.length > 0 && (
                <div className="glass rounded-2xl p-6">
                  <h2 className="font-semibold text-primary mb-4 flex items-center gap-2">
                    <BarChart2 size={16} className="text-purple-400" /> Query Types
                  </h2>
                  <ResponsiveContainer width="100%" height={180}>
                    <PieChart>
                      <Pie
                        data={typeData}
                        cx="50%" cy="50%"
                        innerRadius={45} outerRadius={70}
                        paddingAngle={5}
                        dataKey="value"
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                        labelLine={false}
                      >
                        {typeData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                      </Pie>
                      <Tooltip contentStyle={{ background: '#0d1427', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8, fontSize: 12 }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          )}

          {/* Quick Actions */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <Link to="/upload" className="glass rounded-2xl p-6 glass-hover flex items-center gap-4">
              <div className="w-12 h-12 gradient-bg rounded-xl flex items-center justify-center">
                <Upload size={22} className="text-white" />
              </div>
              <div>
                <p className="font-semibold text-primary">Upload Data</p>
                <p className="text-sm text-secondary">Import CSV or Excel files</p>
              </div>
            </Link>
            <Link to="/chat" className="glass rounded-2xl p-6 glass-hover flex items-center gap-4">
              <div className="w-12 h-12 bg-purple-500/20 rounded-xl flex items-center justify-center border border-purple-500/30">
                <MessageSquare size={22} className="text-purple-400" />
              </div>
              <div>
                <p className="font-semibold text-primary">Ask a Question</p>
                <p className="text-sm text-secondary">Natural language to SQL</p>
              </div>
            </Link>
            <Link to="/history" className="glass rounded-2xl p-6 glass-hover flex items-center gap-4">
              <div className="w-12 h-12 bg-green-500/20 rounded-xl flex items-center justify-center border border-green-500/30">
                <History size={22} className="text-green-400" />
              </div>
              <div>
                <p className="font-semibold text-primary">View History</p>
                <p className="text-sm text-secondary">Browse all past queries</p>
              </div>
            </Link>
          </div>

          {/* Tables + Top Queried */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Tables */}
            <div className="glass rounded-2xl p-6">
              <h2 className="font-semibold text-primary mb-4 flex items-center gap-2">
                <Table2 size={16} className="text-blue-400" /> Loaded Tables ({tables.length})
              </h2>
              {tables.length === 0 ? (
                <p className="text-secondary text-sm">No tables yet — <Link to="/upload" className="text-blue-400 hover:underline">upload a file</Link>.</p>
              ) : (
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {tables.map((t, i) => (
                    <Link
                      key={i}
                      to="/chat"
                      className="flex items-center gap-3 p-3 glass rounded-xl glass-hover text-sm text-primary"
                    >
                      <Database size={14} className="text-blue-400" />
                      <span className="font-mono">{t}</span>
                    </Link>
                  ))}
                </div>
              )}
            </div>

            {/* Top queried tables */}
            <div className="glass rounded-2xl p-6">
              <h2 className="font-semibold text-primary mb-4 flex items-center gap-2">
                <TrendingUp size={16} className="text-purple-400" /> Most Queried Tables
              </h2>
              {!analytics?.top_tables?.length ? (
                <p className="text-secondary text-sm">Run some queries to see stats here.</p>
              ) : (
                <div className="space-y-3">
                  {analytics.top_tables.map((t, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <span className="text-xs text-muted-custom w-4">{i + 1}</span>
                      <span className="font-mono text-sm text-primary flex-1">{t.table}</span>
                      <div className="flex items-center gap-2">
                        <div
                          className="h-1.5 rounded-full gradient-bg"
                          style={{ width: `${Math.round((t.count / analytics.top_tables[0].count) * 80)}px` }}
                        />
                        <span className="text-xs text-muted-custom">{t.count}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </main>
    </div>
  )
}
