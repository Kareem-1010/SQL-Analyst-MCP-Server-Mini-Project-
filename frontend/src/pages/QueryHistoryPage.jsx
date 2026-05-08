import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ArrowLeft, Search, CheckCircle, AlertCircle, Clock,
  Database, RefreshCw, ChevronDown, ChevronUp, Filter, Download
} from 'lucide-react'
import { getHistory, runQuery } from '../services/api'
import { useToast } from '../components/Toast'

export default function QueryHistoryPage() {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [expandedId, setExpandedId] = useState(null)
  const [rerunning, setRerunning] = useState(null)
  const toast = useToast()

  useEffect(() => {
    setLoading(true)
    getHistory(100)
      .then((r) => setHistory(Array.isArray(r.data) ? r.data : []))
      .catch(() => toast.error('Failed to load history'))
      .finally(() => setLoading(false))
  }, [])

  const filtered = history.filter((h) => {
    const matchSearch =
      h.user_query?.toLowerCase().includes(search.toLowerCase()) ||
      h.generated_sql?.toLowerCase().includes(search.toLowerCase())
    const matchStatus = statusFilter === 'all' || h.status === statusFilter
    return matchSearch && matchStatus
  })

  const rerun = async (query) => {
    setRerunning(query.id)
    try {
      await runQuery(query.user_query)
      toast.success('Query re-executed! Check Chat page for results.')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Re-run failed')
    } finally {
      setRerunning(null) }
  }

  const exportCSV = () => {
    const headers = 'id,user_query,generated_sql,status,row_count,execution_time_ms,created_at'
    const rows = history.map(h =>
      [h.id, `"${(h.user_query||'').replace(/"/g,'""')}"`,
       `"${(h.generated_sql||'').replace(/"/g,'""')}"`,
       h.status, h.row_count, h.execution_time_ms, h.created_at].join(',')
    ).join('\n')
    const blob = new Blob([headers + '\n' + rows], { type: 'text/csv' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'query_history.csv'
    a.click()
  }

  const successCount = history.filter(h => h.status === 'success').length
  const errorCount   = history.filter(h => h.status === 'error').length

  return (
    <div className="min-h-screen bg-primary p-6">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Link to="/dashboard" className="glass glass-hover p-2 rounded-xl">
            <ArrowLeft size={18} className="text-secondary" />
          </Link>
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-primary">Query History</h1>
            <p className="text-secondary text-sm">{history.length} total queries</p>
          </div>
          <button
            onClick={exportCSV}
            className="flex items-center gap-2 glass glass-hover px-3 py-2 rounded-xl text-sm text-secondary"
          >
            <Download size={14} /> Export CSV
          </button>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          {[
            { label: 'Total',     value: history.length,  color: 'text-blue-400',   icon: <Database size={16} /> },
            { label: 'Success',   value: successCount,    color: 'text-green-400',  icon: <CheckCircle size={16} /> },
            { label: 'Errors',    value: errorCount,      color: 'text-red-400',    icon: <AlertCircle size={16} /> },
          ].map((s) => (
            <div key={s.label} className="glass rounded-2xl p-4 flex items-center gap-3">
              <span className={s.color}>{s.icon}</span>
              <div>
                <p className="text-xl font-bold text-primary">{s.value}</p>
                <p className="text-xs text-secondary">{s.label}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Filters */}
        <div className="glass rounded-2xl p-4 mb-4 flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-custom" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search queries or SQL…"
              className="w-full glass rounded-xl pl-9 pr-3 py-2 text-sm text-primary placeholder:text-muted-custom focus:outline-none"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter size={14} className="text-muted-custom" />
            {['all', 'success', 'error'].map((s) => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all ${
                  statusFilter === s ? 'gradient-bg text-white' : 'glass text-secondary glass-hover'
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {/* History list */}
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="w-8 h-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="glass rounded-2xl p-12 text-center">
            <Clock size={40} className="text-muted-custom mx-auto mb-3" />
            <p className="text-secondary">No queries found</p>
          </div>
        ) : (
          <div className="space-y-3">
            <AnimatePresence>
              {filtered.map((h) => (
                <motion.div
                  key={h.id}
                  layout
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`glass rounded-2xl overflow-hidden border ${
                    h.status === 'success' ? 'border-green-500/10' : 'border-red-500/10'
                  }`}
                >
                  <div className="p-4">
                    <div className="flex items-start gap-3">
                      <span className="mt-0.5 shrink-0">
                        {h.status === 'success'
                          ? <CheckCircle size={16} className="text-green-400" />
                          : <AlertCircle size={16} className="text-red-400" />
                        }
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-primary font-medium truncate">{h.user_query}</p>
                        <div className="flex items-center gap-3 mt-1 text-xs text-muted-custom">
                          {h.row_count != null && <span>{h.row_count} rows</span>}
                          {h.execution_time_ms != null && <span>{Math.round(h.execution_time_ms)}ms</span>}
                          <span>{h.created_at ? new Date(h.created_at).toLocaleString() : ''}</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <Link
                          to="/chat"
                          state={{ prefill: h.user_query }}
                          onClick={() => {}} 
                          className="glass glass-hover px-2.5 py-1 rounded-lg text-xs text-blue-400 flex items-center gap-1"
                        >
                          <RefreshCw size={11} /> Re-run
                        </Link>
                        <button
                          onClick={() => setExpandedId(expandedId === h.id ? null : h.id)}
                          className="text-muted-custom hover:text-primary transition-colors"
                        >
                          {expandedId === h.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </button>
                      </div>
                    </div>

                    <AnimatePresence>
                      {expandedId === h.id && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className="overflow-hidden mt-3"
                        >
                          {h.generated_sql && (
                            <pre className="code-block text-xs whitespace-pre-wrap mb-2">
                              {h.generated_sql}
                            </pre>
                          )}
                          {h.error_message && (
                            <div className="glass rounded-xl px-3 py-2 border border-red-500/20">
                              <p className="text-xs text-red-400">{h.error_message}</p>
                            </div>
                          )}
                          {h.result_summary && (
                            <p className="text-xs text-muted-custom mt-1">{h.result_summary}</p>
                          )}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  )
}
