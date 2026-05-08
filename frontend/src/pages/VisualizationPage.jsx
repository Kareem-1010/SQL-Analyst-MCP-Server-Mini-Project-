import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, BarChart2 } from 'lucide-react'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import { getTables, callMCPTool } from '../services/api'

const COLORS = ['#4f8ef7', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444']

export default function VisualizationPage() {
  const [tables, setTables] = useState([])
  const [selectedTable, setSelectedTable] = useState('')
  const [rows, setRows] = useState([])
  const [columns, setColumns] = useState([])
  const [chartType, setChartType] = useState('bar')
  const [xCol, setXCol] = useState('')
  const [yCols, setYCols] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getTables().then(r => {
      const t = r.data.tables || []
      setTables(t)
      if (t.length > 0) { setSelectedTable(t[0]) }
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (!selectedTable) return
    setLoading(true)
    callMCPTool('select_data', { table_name: selectedTable, limit: 200 })
      .then(r => {
        const data = r.data?.data?.rows || []
        setRows(data)
        if (data.length > 0) {
          const cols = Object.keys(data[0])
          setColumns(cols)
          const numericCols = cols.filter(c => typeof data[0][c] === 'number')
          const strCols = cols.filter(c => typeof data[0][c] === 'string')
          setXCol(strCols[0] || cols[0])
          setYCols(numericCols.slice(0, 3))
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [selectedTable])

  const chartData = rows.slice(0, 30).map(r => ({
    name: xCol ? String(r[xCol]).slice(0, 12) : '',
    ...yCols.reduce((acc, c) => ({ ...acc, [c]: r[c] }), {})
  }))

  return (
    <div className="min-h-screen bg-primary p-6">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Link to="/dashboard" className="glass glass-hover p-2 rounded-xl">
            <ArrowLeft size={18} className="text-secondary" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-primary">Visualisation</h1>
            <p className="text-secondary text-sm">Explore your data with interactive charts</p>
          </div>
        </div>

        {/* Controls */}
        <div className="glass rounded-2xl p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="text-xs text-secondary mb-1 block">Table</label>
              <select
                value={selectedTable}
                onChange={e => setSelectedTable(e.target.value)}
                className="w-full glass text-sm text-primary px-3 py-2 rounded-xl focus:outline-none"
              >
                {tables.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-secondary mb-1 block">X Axis</label>
              <select
                value={xCol}
                onChange={e => setXCol(e.target.value)}
                className="w-full glass text-sm text-primary px-3 py-2 rounded-xl focus:outline-none"
              >
                {columns.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-secondary mb-1 block">Y Axis</label>
              <select
                value={yCols[0] || ''}
                onChange={e => setYCols([e.target.value])}
                className="w-full glass text-sm text-primary px-3 py-2 rounded-xl focus:outline-none"
              >
                {columns.filter(c => typeof rows[0]?.[c] === 'number').map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-secondary mb-1 block">Chart Type</label>
              <div className="flex gap-1">
                {['bar', 'line', 'pie'].map(t => (
                  <button
                    key={t}
                    onClick={() => setChartType(t)}
                    className={`flex-1 py-2 text-xs font-medium rounded-lg transition-all capitalize ${
                      chartType === t ? 'gradient-bg text-white' : 'glass text-secondary glass-hover'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Chart */}
        <motion.div
          key={chartType + selectedTable}
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          className="glass rounded-2xl p-6"
          style={{ height: 420 }}
        >
          {loading ? (
            <div className="flex items-center justify-center h-full gap-3">
              <div className="w-6 h-6 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
              <span className="text-secondary">Loading data…</span>
            </div>
          ) : chartData.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full">
              <BarChart2 size={40} className="text-muted-custom mb-3" />
              <p className="text-secondary">No data to visualise. Upload a file first.</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              {chartType === 'bar' ? (
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
                  <Tooltip contentStyle={{ background: '#0d1427', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8 }} />
                  <Legend />
                  {yCols.map((c, i) => <Bar key={c} dataKey={c} fill={COLORS[i % COLORS.length]} radius={[4, 4, 0, 0]} />)}
                </BarChart>
              ) : chartType === 'line' ? (
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
                  <Tooltip contentStyle={{ background: '#0d1427', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8 }} />
                  <Legend />
                  {yCols.map((c, i) => (
                    <Line key={c} type="monotone" dataKey={c} stroke={COLORS[i % COLORS.length]} strokeWidth={2} dot={{ r: 3 }} />
                  ))}
                </LineChart>
              ) : (
                <PieChart>
                  <Pie
                    data={chartData}
                    dataKey={yCols[0]}
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={150}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(1)}%`}
                  >
                    {chartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: '#0d1427', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8 }} />
                  <Legend />
                </PieChart>
              )}
            </ResponsiveContainer>
          )}
        </motion.div>

        {/* Row count info */}
        {rows.length > 0 && (
          <p className="text-xs text-muted-custom mt-3 text-center">
            Showing up to 30 of {rows.length} rows from <span className="font-mono text-blue-400">{selectedTable}</span>
          </p>
        )}
      </div>
    </div>
  )
}
